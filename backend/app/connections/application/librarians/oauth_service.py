"""Application service for librarian OAuth provider lifecycle."""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from typing import Final

from app.connections.application.librarians.oauth_client import OAuthProviderClient
from app.connections.domain.contracts.librarian_oauth_contracts import (
    OAuthDeviceAuthorization,
    OAuthPollResult,
    OAuthTokenSet,
)
from app.connections.domain.entities.read_models import LibrarianProvider
from app.connections.domain.event_enum.provider_enums import (
    AuthType,
    OAuthConnectionStatus,
    OAuthPollStatus,
    ProviderSecretKey,
    ProviderType,
)
from app.connections.domain.repositories.librarian_repository import (
    ILibrarianProviderRepository,
    IProviderSecretRepository,
)
from app.connections.domain.types.librarian_oauth_payload_types import (
    LibrarianOAuthStartPayload,
    LibrarianOAuthStatusPayload,
)
from app.shared.exceptions import NotFoundError, UnsupportedProviderError
from app.shared.types.types_convert_utils import now_utc

OAUTH_REFRESH_SKEW: Final[timedelta] = timedelta(seconds=120)
_DEVICE_FLOW_SECRET_KEYS: Final[tuple[ProviderSecretKey, ...]] = (
    ProviderSecretKey.OAUTH_DEVICE_CODE,
    ProviderSecretKey.OAUTH_DEVICE_EXPIRES_AT,
    ProviderSecretKey.OAUTH_POLL_INTERVAL_SECONDS,
)
_ALL_PROVIDER_SECRET_KEYS: Final[tuple[ProviderSecretKey, ...]] = tuple(
    ProviderSecretKey
)


class LibrarianOAuthService:
    """Orchestrate OAuth lifecycle for Codex/GPT librarian providers."""

    def __init__(
        self,
        provider_repo: ILibrarianProviderRepository,
        secret_repo: IProviderSecretRepository,
        oauth_client: OAuthProviderClient,
        now_provider: Callable[[], datetime] = now_utc,
    ) -> None:
        """Initialize OAuth service boundaries.

        Args:
            provider_repo: Provider metadata repository.
            secret_repo: Encrypted provider secret repository.
            oauth_client: External OAuth provider boundary.
            now_provider: Clock boundary for deterministic expiry tests.
        """
        self.provider_repo = provider_repo
        self.secret_repo = secret_repo
        self.oauth_client = oauth_client
        self.now_provider = now_provider

    async def start_oauth(self, provider_id: str) -> LibrarianOAuthStartPayload:
        """Start a device OAuth flow for an OPENAI_CODEX provider.

        Args:
            provider_id: Provider id.

        Returns:
            LibrarianOAuthStartPayload: User-facing device authorization details.
        """
        provider = await self._load_codex_oauth_provider(provider_id)
        authorization = await self.oauth_client.start_device_authorization(provider)
        await self._store_device_authorization(provider.id, authorization)
        payload = LibrarianOAuthStartPayload(
            provider_id=provider.id,
            status=OAuthPollStatus.PENDING,
            user_code=authorization.user_code,
            verification_uri=authorization.verification_uri,
            verification_uri_complete=authorization.verification_uri_complete,
            expires_at=authorization.expires_at,
            interval_seconds=authorization.interval_seconds,
        )
        return payload

    async def poll_oauth(self, provider_id: str) -> LibrarianOAuthStatusPayload:
        """Poll a pending OAuth device flow and persist tokens on success.

        Args:
            provider_id: Provider id.

        Returns:
            LibrarianOAuthStatusPayload: Public connection status.
        """
        provider = await self._load_codex_oauth_provider(provider_id)
        device_code = await self._resolve_secret(
            provider.id,
            ProviderSecretKey.OAUTH_DEVICE_CODE,
        )
        if device_code is None:
            raise UnsupportedProviderError("OAuth device flow has not been started")

        device_expires_at = await self._device_expires_at(provider.id)
        if device_expires_at is not None and device_expires_at <= self._now():
            await self._delete_secrets(provider.id, _DEVICE_FLOW_SECRET_KEYS)
            return self._status_payload(
                provider_id=provider.id,
                status=OAuthConnectionStatus.EXPIRED,
                connected=False,
                expires_at=None,
                refresh_required=False,
                message="OAuth device flow expired",
            )

        poll_result = await self.oauth_client.poll_device_token(provider, device_code)
        payload = await self._handle_poll_result(provider, poll_result)
        return payload

    async def get_oauth_status(
        self,
        provider_id: str,
    ) -> LibrarianOAuthStatusPayload:
        """Return public OAuth connection state without token material.

        Args:
            provider_id: Provider id.

        Returns:
            LibrarianOAuthStatusPayload: Public connection status.
        """
        provider = await self._load_codex_oauth_provider(provider_id)
        payload = await self._current_status(provider.id)
        return payload

    async def refresh_if_needed(
        self,
        provider_id: str,
    ) -> LibrarianOAuthStatusPayload:
        """Refresh a provider token only when it is missing or near expiry.

        Args:
            provider_id: Provider id.

        Returns:
            LibrarianOAuthStatusPayload: Public status after refresh evaluation.
        """
        provider = await self._load_codex_oauth_provider(provider_id)
        current_status = await self._current_status(provider.id)
        if current_status["status"] is OAuthConnectionStatus.CONNECTED:
            return current_status

        if current_status["status"] not in {
            OAuthConnectionStatus.REFRESH_REQUIRED,
            OAuthConnectionStatus.EXPIRED,
            OAuthConnectionStatus.MISSING_REFRESH_TOKEN,
        }:
            return current_status

        refresh_token = await self._resolve_secret(
            provider.id,
            ProviderSecretKey.OAUTH_REFRESH_TOKEN,
        )
        if refresh_token is None:
            return self._status_payload(
                provider_id=provider.id,
                status=OAuthConnectionStatus.MISSING_REFRESH_TOKEN,
                connected=False,
                expires_at=current_status["expires_at"],
                refresh_required=False,
                message="OAuth refresh token is missing",
            )

        token_set = await self.oauth_client.refresh_token(provider, refresh_token)
        await self._store_token_set(provider.id, token_set)
        payload = self._status_payload(
            provider_id=provider.id,
            status=OAuthConnectionStatus.CONNECTED,
            connected=True,
            expires_at=token_set.expires_at,
            refresh_required=False,
            message=None,
        )
        return payload

    async def delete_oauth_secrets(self, provider_id: str) -> None:
        """Delete all known provider credential keys.

        Args:
            provider_id: Provider id.

        Returns:
            None.
        """
        await self._delete_secrets(provider_id, _ALL_PROVIDER_SECRET_KEYS)

    async def _load_codex_oauth_provider(self, provider_id: str) -> LibrarianProvider:
        row = await self.provider_repo.get(provider_id)
        if row is None:
            raise NotFoundError(f"Provider not found: {provider_id}")

        if not isinstance(row.provider_type, ProviderType) or not isinstance(
            row.auth_type, AuthType
        ):
            raise UnsupportedProviderError(
                f"Provider type {row.provider_type} does not support OAuth lifecycle"
            )
        provider_type = row.provider_type
        auth_type = row.auth_type
        if (
            provider_type is not ProviderType.OPENAI_CODEX
            or auth_type is not AuthType.OAUTH
        ):
            raise UnsupportedProviderError(
                f"Provider type {provider_type.value} does not support OAuth lifecycle"
            )
        return row

    async def _store_device_authorization(
        self,
        provider_id: str,
        authorization: OAuthDeviceAuthorization,
    ) -> None:
        await self._set_secret(
            provider_id,
            ProviderSecretKey.OAUTH_DEVICE_CODE,
            authorization.device_code,
        )
        await self._set_secret(
            provider_id,
            ProviderSecretKey.OAUTH_DEVICE_EXPIRES_AT,
            self._format_datetime(authorization.expires_at),
        )
        await self._set_secret(
            provider_id,
            ProviderSecretKey.OAUTH_POLL_INTERVAL_SECONDS,
            str(authorization.interval_seconds),
        )

    async def _handle_poll_result(
        self,
        provider: LibrarianProvider,
        poll_result: OAuthPollResult,
    ) -> LibrarianOAuthStatusPayload:
        if poll_result.status is OAuthPollStatus.CONNECTED:
            if poll_result.token_set is None:
                raise UnsupportedProviderError("OAuth provider did not return tokens")
            await self._store_token_set(provider.id, poll_result.token_set)
            await self._delete_secrets(provider.id, _DEVICE_FLOW_SECRET_KEYS)
            return self._status_payload(
                provider_id=provider.id,
                status=OAuthConnectionStatus.CONNECTED,
                connected=True,
                expires_at=poll_result.token_set.expires_at,
                refresh_required=False,
                message=None,
            )

        if poll_result.status is OAuthPollStatus.EXPIRED:
            await self._delete_secrets(provider.id, _DEVICE_FLOW_SECRET_KEYS)
            return self._status_payload(
                provider_id=provider.id,
                status=OAuthConnectionStatus.EXPIRED,
                connected=False,
                expires_at=None,
                refresh_required=False,
                message=poll_result.message,
            )

        if poll_result.status is OAuthPollStatus.FAILED:
            return self._status_payload(
                provider_id=provider.id,
                status=OAuthConnectionStatus.FAILED,
                connected=False,
                expires_at=None,
                refresh_required=False,
                message=poll_result.message,
            )

        return self._status_payload(
            provider_id=provider.id,
            status=OAuthConnectionStatus.PENDING,
            connected=False,
            expires_at=None,
            refresh_required=False,
            message=poll_result.message,
        )

    async def _current_status(self, provider_id: str) -> LibrarianOAuthStatusPayload:
        device_code = await self._resolve_secret(
            provider_id,
            ProviderSecretKey.OAUTH_DEVICE_CODE,
        )
        if device_code is not None:
            device_expires_at = await self._device_expires_at(provider_id)
            if device_expires_at is None or device_expires_at > self._now():
                return self._status_payload(
                    provider_id=provider_id,
                    status=OAuthConnectionStatus.PENDING,
                    connected=False,
                    expires_at=None,
                    refresh_required=False,
                    message=None,
                )
            await self._delete_secrets(provider_id, _DEVICE_FLOW_SECRET_KEYS)
            return self._status_payload(
                provider_id=provider_id,
                status=OAuthConnectionStatus.EXPIRED,
                connected=False,
                expires_at=None,
                refresh_required=False,
                message="OAuth device flow expired",
            )

        access_token = await self._resolve_secret(
            provider_id,
            ProviderSecretKey.OAUTH_ACCESS_TOKEN,
        )
        expires_at = await self._token_expires_at(provider_id)
        refresh_token = await self._resolve_secret(
            provider_id,
            ProviderSecretKey.OAUTH_REFRESH_TOKEN,
        )
        if access_token is None:
            return self._status_payload(
                provider_id=provider_id,
                status=OAuthConnectionStatus.NOT_CONNECTED,
                connected=False,
                expires_at=expires_at,
                refresh_required=False,
                message=None,
            )
        if expires_at is None:
            return self._missing_expiry_payload(provider_id, refresh_token)
        if expires_at <= self._now():
            if refresh_token is None:
                return self._status_payload(
                    provider_id=provider_id,
                    status=OAuthConnectionStatus.EXPIRED,
                    connected=False,
                    expires_at=expires_at,
                    refresh_required=False,
                    message="OAuth access token expired",
                )
            return self._refresh_required_payload(provider_id, expires_at)
        if expires_at <= self._now() + OAUTH_REFRESH_SKEW:
            if refresh_token is None:
                return self._status_payload(
                    provider_id=provider_id,
                    status=OAuthConnectionStatus.MISSING_REFRESH_TOKEN,
                    connected=False,
                    expires_at=expires_at,
                    refresh_required=False,
                    message="OAuth refresh token is missing",
                )
            return self._refresh_required_payload(provider_id, expires_at)
        return self._status_payload(
            provider_id=provider_id,
            status=OAuthConnectionStatus.CONNECTED,
            connected=True,
            expires_at=expires_at,
            refresh_required=False,
            message=None,
        )

    def _missing_expiry_payload(
        self,
        provider_id: str,
        refresh_token: str | None,
    ) -> LibrarianOAuthStatusPayload:
        if refresh_token is None:
            return self._status_payload(
                provider_id=provider_id,
                status=OAuthConnectionStatus.EXPIRED,
                connected=False,
                expires_at=None,
                refresh_required=False,
                message="OAuth token expiry is missing",
            )
        return self._refresh_required_payload(provider_id, None)

    def _refresh_required_payload(
        self,
        provider_id: str,
        expires_at: datetime | None,
    ) -> LibrarianOAuthStatusPayload:
        return self._status_payload(
            provider_id=provider_id,
            status=OAuthConnectionStatus.REFRESH_REQUIRED,
            connected=True,
            expires_at=expires_at,
            refresh_required=True,
            message=None,
        )

    async def _store_token_set(
        self,
        provider_id: str,
        token_set: OAuthTokenSet,
    ) -> None:
        await self._set_secret(
            provider_id,
            ProviderSecretKey.OAUTH_ACCESS_TOKEN,
            token_set.access_token,
        )
        if token_set.refresh_token is not None:
            await self._set_secret(
                provider_id,
                ProviderSecretKey.OAUTH_REFRESH_TOKEN,
                token_set.refresh_token,
            )
        await self._set_secret(
            provider_id,
            ProviderSecretKey.OAUTH_EXPIRES_AT,
            self._format_datetime(token_set.expires_at),
        )
        await self._set_secret(
            provider_id,
            ProviderSecretKey.OAUTH_TOKEN_TYPE,
            token_set.token_type,
        )
        if token_set.scope is not None:
            await self._set_secret(
                provider_id,
                ProviderSecretKey.OAUTH_SCOPE,
                token_set.scope,
            )

    async def _token_expires_at(self, provider_id: str) -> datetime | None:
        value = await self._resolve_secret(
            provider_id,
            ProviderSecretKey.OAUTH_EXPIRES_AT,
        )
        return self._parse_datetime(value)

    async def _device_expires_at(self, provider_id: str) -> datetime | None:
        value = await self._resolve_secret(
            provider_id,
            ProviderSecretKey.OAUTH_DEVICE_EXPIRES_AT,
        )
        return self._parse_datetime(value)

    async def _resolve_secret(
        self,
        provider_id: str,
        key: ProviderSecretKey,
    ) -> str | None:
        value = await self.secret_repo.resolve(provider_id, key.value)
        return value

    async def _set_secret(
        self,
        provider_id: str,
        key: ProviderSecretKey,
        value: str,
    ) -> None:
        await self.secret_repo.set_secret(
            provider_id=provider_id,
            key_name=key.value,
            value=value,
        )

    async def _delete_secrets(
        self,
        provider_id: str,
        keys: tuple[ProviderSecretKey, ...],
    ) -> None:
        for key in keys:
            await self.secret_repo.delete_for_provider(provider_id, key.value)

    def _now(self) -> datetime:
        current = self.now_provider()
        if current.tzinfo is None:
            return current.replace(tzinfo=UTC)
        return current

    def _parse_datetime(self, value: str | None) -> datetime | None:
        if value is None:
            return None
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None
        if parsed.tzinfo is None:
            return parsed.replace(tzinfo=UTC)
        return parsed

    def _format_datetime(self, value: datetime) -> str:
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC).isoformat()
        return value.isoformat()

    def _status_payload(
        self,
        provider_id: str,
        status: OAuthConnectionStatus,
        connected: bool,
        expires_at: datetime | None,
        refresh_required: bool,
        message: str | None,
    ) -> LibrarianOAuthStatusPayload:
        return LibrarianOAuthStatusPayload(
            provider_id=provider_id,
            status=status,
            connected=connected,
            expires_at=expires_at,
            refresh_required=refresh_required,
            message=message,
        )
