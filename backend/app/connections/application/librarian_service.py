"""Librarian provider configuration service."""

from __future__ import annotations

from app.connections.application.librarians.credential_policy import (
    ensure_create_credentials_are_present,
    ensure_openai_codex_oauth_config_is_safe,
    ensure_provider_auth_type_is_supported,
    ensure_provider_config_has_no_credentials,
    openai_codex_oauth_config_has_protected_change,
)
from app.connections.application.librarians.provider_payload_mapper import (
    build_provider_payload,
)
from app.connections.domain.contracts.librarian_client_contracts import (
    LibrarianProviderClientFactory,
)
from app.connections.domain.contracts.librarian_provider_contracts import (
    LibrarianProviderCreate,
    LibrarianProviderUpdate,
)
from app.connections.domain.entities.read_models import LibrarianProvider
from app.connections.domain.event_enum.provider_enums import (
    AuthType,
    ProviderSecretKey,
    ProviderType,
)
from app.connections.domain.repositories.librarian_repository import (
    ILibrarianProviderRepository,
    IProviderSecretRepository,
)
from app.connections.domain.types.librarian_provider_payload_types import (
    LibrarianProviderPatchPayload,
    LibrarianProviderPayload,
    LibrarianProviderPayloadList,
    LibrarianProviderTestPayload,
    LibrarianProviderUpdateValues,
)
from app.shared.exceptions import (
    BoundaryValidationError,
    ConnectionsProviderUnsupportedError,
    ConnectionsResourceNotFoundError,
)
from app.shared.types.extra_types import JSONObject
from app.shared.types.types_convert_utils import enum_value, now_utc

_ALL_PROVIDER_SECRET_KEYS = tuple(ProviderSecretKey)
_OAUTH_PROVIDER_SECRET_KEYS = (
    ProviderSecretKey.OAUTH_ACCESS_TOKEN,
    ProviderSecretKey.OAUTH_REFRESH_TOKEN,
    ProviderSecretKey.OAUTH_EXPIRES_AT,
    ProviderSecretKey.OAUTH_TOKEN_TYPE,
    ProviderSecretKey.OAUTH_SCOPE,
    ProviderSecretKey.OAUTH_DEVICE_CODE,
    ProviderSecretKey.OAUTH_DEVICE_EXPIRES_AT,
    ProviderSecretKey.OAUTH_POLL_INTERVAL_SECONDS,
)


def _provider_identity(row: LibrarianProvider) -> tuple[ProviderType, AuthType]:
    """Parse persisted provider identity without ad-hoc runtime type checks.

    Args:
        row: Provider read model loaded from the repository.

    Returns:
        tuple[ProviderType, AuthType]: Parsed provider/auth identity.
    """
    try:
        provider_type = enum_value(row.provider_type, ProviderType, "provider_type")
        auth_type = enum_value(row.auth_type, AuthType, "auth_type")
    except BoundaryValidationError as exc:
        raise ConnectionsProviderUnsupportedError(
            f"Provider type {row.provider_type} is unsupported"
        ) from exc
    return provider_type, auth_type


def _provider_update_values(
    payload: LibrarianProviderPatchPayload,
) -> LibrarianProviderUpdateValues:
    """Build provider patch values without secret fields.

    Args:
        payload: Service-layer patch payload.

    Returns:
        LibrarianProviderUpdateValues: Provider fields safe for repository update.
    """
    values: LibrarianProviderUpdateValues = {}
    if "name" in payload:
        values["name"] = payload["name"]
    if "provider_type" in payload:
        values["provider_type"] = enum_value(
            payload["provider_type"], ProviderType, "provider_type"
        )
    if "auth_type" in payload:
        values["auth_type"] = enum_value(payload["auth_type"], AuthType, "auth_type")
    if "enabled" in payload:
        values["enabled"] = payload["enabled"]
    if "config" in payload:
        values["config"] = payload["config"]
    return values


class LibrarianService:
    """Service to orchestrate librarian provider settings and usage."""

    def __init__(
        self,
        provider_repo: ILibrarianProviderRepository,
        secret_repo: IProviderSecretRepository,
        client_factory: LibrarianProviderClientFactory,
    ) -> None:
        """Initialize librarian service dependencies.

        Args:
            provider_repo: Provider persistence port.
            secret_repo: Provider secret persistence port.
            client_factory: Provider test client factory.
        """
        self.provider_repo = provider_repo
        self.secret_repo = secret_repo
        self.client_factory = client_factory

    async def create_provider(
        self,
        name: str,
        provider_type: ProviderType,
        auth_type: AuthType,
        enabled: bool,
        config: JSONObject,
        api_key: str | None,
        oauth_access_token: str | None,
    ) -> LibrarianProviderPayload:
        """Create provider and store secrets by provider/auth type.

        Args:
            name: Friendly name.
            provider_type: Provider implementation family.
            auth_type: Authentication mode.
            enabled: Provider enabled flag.
            config: Provider config payload.
            api_key: Optional API key.
            oauth_access_token: Optional OAuth token.

        Returns:
            Provider payload map.
        """
        provider_type = enum_value(provider_type, ProviderType, "provider_type")
        auth_type = enum_value(auth_type, AuthType, "auth_type")
        ensure_provider_config_has_no_credentials(config)
        ensure_openai_codex_oauth_config_is_safe(
            provider_type=provider_type,
            auth_type=auth_type,
            config=config,
        )
        ensure_create_credentials_are_present(
            provider_type=provider_type,
            auth_type=auth_type,
            api_key=api_key,
            oauth_access_token=oauth_access_token,
        )

        now = now_utc()
        model = await self.provider_repo.create(
            payload=LibrarianProviderCreate(
                name=name,
                provider_type=provider_type,
                auth_type=auth_type,
                enabled=enabled,
                config=config,
                created_at=now,
                updated_at=now,
            ),
        )

        if auth_type is AuthType.API_KEY and api_key:
            await self.secret_repo.set_secret(
                provider_id=model.id,
                key_name=ProviderSecretKey.API_KEY.value,
                value=api_key,
            )
        if auth_type is AuthType.OAUTH and oauth_access_token:
            await self.secret_repo.set_secret(
                provider_id=model.id,
                key_name=ProviderSecretKey.OAUTH_ACCESS_TOKEN.value,
                value=oauth_access_token,
            )

        return build_provider_payload(model)

    async def list_providers(self) -> LibrarianProviderPayloadList:
        """List all providers for response payloads.

        Args:
            None.

        Returns:
            LibrarianProviderPayloadList: Provider payloads without secrets.
        """
        providers = await self.provider_repo.list_all()
        return [build_provider_payload(row) for row in providers]

    async def get_provider(self, provider_id: str) -> LibrarianProviderPayload:
        """Load one provider.

        Args:
            provider_id: Provider id.

        Returns:
            Provider payload dictionary.
        """
        row = await self.provider_repo.get(provider_id)
        if row is None:
            raise ConnectionsResourceNotFoundError(f"Provider not found: {provider_id}")
        return build_provider_payload(row)

    async def update_provider(
        self,
        provider_id: str,
        payload: LibrarianProviderPatchPayload,
    ) -> LibrarianProviderPayload:
        """Patch provider configuration and optional credentials.

        Args:
            provider_id: Provider id.
            payload: Updatable payload with optional secret fields.

        Returns:
            LibrarianProviderPayload: Updated provider payload without secrets.
        """
        row = await self.provider_repo.get(provider_id)
        if row is None:
            raise ConnectionsResourceNotFoundError(f"Provider not found: {provider_id}")

        if "config" in payload:
            ensure_provider_config_has_no_credentials(payload["config"])

        api_key = payload.get("api_key")
        oauth_access_token = payload.get("oauth_access_token")
        current_provider_type, current_auth_type = _provider_identity(row)
        provider_type = enum_value(
            payload.get("provider_type", current_provider_type),
            ProviderType,
            "provider_type",
        )
        auth_type = enum_value(
            payload.get("auth_type", current_auth_type),
            AuthType,
            "auth_type",
        )
        ensure_provider_auth_type_is_supported(
            provider_type=provider_type,
            auth_type=auth_type,
        )
        next_config = payload.get("config", row.config)
        ensure_openai_codex_oauth_config_is_safe(
            provider_type=provider_type,
            auth_type=auth_type,
            config=next_config,
        )
        identity_changed = (
            provider_type is not current_provider_type
            or auth_type is not current_auth_type
        )

        if auth_type is AuthType.API_KEY and api_key is None:
            if identity_changed:
                raise ConnectionsProviderUnsupportedError(
                    "API_KEY auth requires api_key"
                )
            existing_api_key = await self.secret_repo.resolve(
                provider_id,
                ProviderSecretKey.API_KEY.value,
            )
            if not existing_api_key:
                raise ConnectionsProviderUnsupportedError(
                    "API_KEY auth requires api_key"
                )

        if (
            current_provider_type is ProviderType.OPENAI_CODEX
            and current_auth_type is AuthType.OAUTH
            and provider_type is ProviderType.OPENAI_CODEX
            and auth_type is AuthType.OAUTH
            and "config" in payload
            and openai_codex_oauth_config_has_protected_change(
                row.config,
                payload["config"],
            )
            and await self._oauth_secret_exists(provider_id)
        ):
            raise ConnectionsProviderUnsupportedError(
                "OAuth endpoint config cannot change while OAuth tokens are stored"
            )

        updated = await self.provider_repo.update(
            provider_id,
            payload=LibrarianProviderUpdate(values=_provider_update_values(payload)),
        )

        if identity_changed:
            await self._delete_all_provider_secrets(provider_id)

        if auth_type is AuthType.API_KEY and api_key is not None:
            await self.secret_repo.set_secret(
                provider_id=provider_id,
                key_name=ProviderSecretKey.API_KEY.value,
                value=api_key,
            )
        if auth_type is AuthType.OAUTH and oauth_access_token is not None:
            await self.secret_repo.set_secret(
                provider_id=provider_id,
                key_name=ProviderSecretKey.OAUTH_ACCESS_TOKEN.value,
                value=oauth_access_token,
            )

        return build_provider_payload(updated)

    async def _oauth_secret_exists(self, provider_id: str) -> bool:
        for key in _OAUTH_PROVIDER_SECRET_KEYS:
            secret = await self.secret_repo.resolve(provider_id, key.value)
            if secret:
                return True
        return False

    async def _delete_all_provider_secrets(self, provider_id: str) -> None:
        for key in _ALL_PROVIDER_SECRET_KEYS:
            await self.secret_repo.delete_for_provider(provider_id, key.value)

    async def delete_provider(self, provider_id: str) -> None:
        """Delete provider and all secrets.

        Args:
            provider_id: Provider id.

        Returns:
            None.
        """
        row = await self.provider_repo.get(provider_id)
        if row is None:
            raise ConnectionsResourceNotFoundError(f"Provider not found: {provider_id}")
        await self._delete_all_provider_secrets(provider_id)
        await self.provider_repo.delete(provider_id)

    async def test_provider(
        self,
        provider_id: str,
        test_query: str,
    ) -> LibrarianProviderTestPayload:
        """Verify provider registration and required credential path.

        Args:
            provider_id: Provider id.
            test_query: Text submitted for a dry run.

        Returns:
            Test result map.
        """
        model = await self.provider_repo.get(provider_id)
        if model is None:
            raise ConnectionsResourceNotFoundError(f"Provider not found: {provider_id}")
        result = await self.client_factory.test_connection(
            provider=model,
            secret_resolver=self.secret_repo,
            test_query=test_query,
        )
        return result.as_public_dict()
