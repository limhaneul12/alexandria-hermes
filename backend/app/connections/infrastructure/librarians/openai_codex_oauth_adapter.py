"""HTTP OAuth device-flow client for OPENAI_CODEX librarian providers."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Final

import httpx
from app.connections.application.librarians.credential_policy import (
    ensure_openai_codex_oauth_config_is_safe,
)
from app.connections.application.librarians.oauth_client import OAuthProviderClient
from app.connections.domain.contracts.librarian_oauth_contracts import (
    OAuthDeviceAuthorization,
    OAuthPollResult,
    OAuthTokenSet,
)
from app.connections.domain.entities.read_models import LibrarianProvider
from app.connections.domain.event_enum.provider_enums import (
    AuthType,
    OAuthPollStatus,
    ProviderType,
)
from app.platform.config.app_config import AppConfig
from app.shared.exceptions import UnsupportedProviderError
from app.shared.serialization.orjson_codec import dumps_json, loads_json
from app.shared.types.extra_types import JSONObject, JSONValue
from typing_extensions import TypedDict

_CODEX_DEVICE_AUTHORIZATION_PATH: Final[str] = "/api/accounts/deviceauth/usercode"
_CODEX_DEVICE_TOKEN_PATH: Final[str] = "/api/accounts/deviceauth/token"
_CODEX_TOKEN_PATH: Final[str] = "/oauth/token"
_CODEX_VERIFICATION_PATH: Final[str] = "/codex/device"
_CODEX_REDIRECT_PATH: Final[str] = "/deviceauth/callback"
_AUTHORIZATION_CODE_GRANT_TYPE = "authorization_code"
_REFRESH_TOKEN_GRANT_TYPE = "refresh_token"


class CodexDeviceAuthorizationRequest(TypedDict, closed=True):
    """Request body for the OpenAI Codex device authorization endpoint."""

    client_id: str


class CodexDevicePollRequest(TypedDict, closed=True):
    """Request body for polling OpenAI Codex device authorization."""

    device_auth_id: str
    user_code: str


class CodexDeviceSecretPayload(TypedDict, closed=True):
    """Secret payload persisted while a Codex device flow is pending."""

    device_auth_id: str
    user_code: str


@dataclass(frozen=True, slots=True)
class OpenAICodexOAuthConfig:
    """Endpoint and client metadata for the OpenAI Codex device flow."""

    device_authorization_url: str
    device_token_url: str
    token_url: str
    client_id: str
    verification_uri: str
    redirect_uri: str


@dataclass(frozen=True, slots=True)
class OpenAICodexOAuthSettings:
    """Runtime OpenAI Codex OAuth metadata loaded from service config."""

    issuer: str
    client_id: str
    device_expires_in_seconds: int
    min_poll_interval_seconds: int

    @classmethod
    def from_app_config(
        cls,
        config: AppConfig | None = None,
    ) -> OpenAICodexOAuthSettings:
        """Build OpenAI Codex OAuth settings from AppConfig.

        Args:
            config: Optional AppConfig supplied by tests or dependency injection.

        Returns:
            OpenAICodexOAuthSettings: Required Codex OAuth runtime metadata.
        """
        app_config = AppConfig() if config is None else config
        return cls(
            issuer=app_config.codex_oauth_issuer.strip().rstrip("/"),
            client_id=app_config.codex_oauth_client_id.strip(),
            device_expires_in_seconds=(
                app_config.codex_oauth_device_expires_in_seconds
            ),
            min_poll_interval_seconds=(
                app_config.codex_oauth_min_poll_interval_seconds
            ),
        )


class OpenAICodexOAuthClient(OAuthProviderClient):
    """OAuth client that follows the Hermes OpenAI Codex device flow."""

    def __init__(self, settings: OpenAICodexOAuthSettings | None = None) -> None:
        """Initialize the client with service-loaded OAuth settings.

        Args:
            settings: Optional OpenAI Codex OAuth settings override.
        """
        self._settings = (
            OpenAICodexOAuthSettings.from_app_config() if settings is None else settings
        )

    async def start_device_authorization(
        self,
        provider: LibrarianProvider,
    ) -> OAuthDeviceAuthorization:
        """Start device authorization at the OpenAI Codex endpoint.

        Args:
            provider: OPENAI_CODEX provider read model.

        Returns:
            OAuthDeviceAuthorization: Device-flow values.
        """
        config = _oauth_config(provider.config, self._settings)
        request_payload = CodexDeviceAuthorizationRequest(client_id=config.client_id)
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                config.device_authorization_url,
                json=request_payload,
                headers={"Content-Type": "application/json"},
            )
        if response.status_code >= 400:
            raise UnsupportedProviderError("OAuth device authorization failed")
        payload = _response_payload(response)

        device_auth_id = _required_string(payload, "device_auth_id")
        user_code = _required_string(payload, "user_code")
        authorization = OAuthDeviceAuthorization(
            device_code=_device_secret_value(
                device_auth_id=device_auth_id,
                user_code=user_code,
            ),
            user_code=user_code,
            verification_uri=config.verification_uri,
            verification_uri_complete=None,
            expires_at=_device_expires_at_from_payload(payload, self._settings),
            interval_seconds=_poll_interval_from_payload(payload, self._settings),
        )
        return authorization

    async def poll_device_token(
        self,
        provider: LibrarianProvider,
        device_code: str,
    ) -> OAuthPollResult:
        """Poll Codex device authorization and exchange code for tokens.

        Args:
            provider: OPENAI_CODEX provider read model.
            device_code: Secret device authorization context.

        Returns:
            OAuthPollResult: Poll status and optional token set.
        """
        config = _oauth_config(provider.config, self._settings)
        device_context = _device_secret_payload(device_code)
        poll_payload = CodexDevicePollRequest(
            device_auth_id=device_context["device_auth_id"],
            user_code=device_context["user_code"],
        )
        async with httpx.AsyncClient(timeout=10.0) as client:
            device_response = await client.post(
                config.device_token_url,
                json=poll_payload,
                headers={"Content-Type": "application/json"},
            )
            if device_response.status_code in {403, 404}:
                return _pending_poll_result()
            if device_response.status_code == 429:
                return _slow_down_poll_result()
            if device_response.status_code >= 400:
                payload = _error_response_payload(device_response)
                return _oauth_error_poll_result(payload)

            code_payload = _response_payload(device_response)
            token_response = await client.post(
                config.token_url,
                data={
                    "grant_type": _AUTHORIZATION_CODE_GRANT_TYPE,
                    "code": _required_string(code_payload, "authorization_code"),
                    "redirect_uri": config.redirect_uri,
                    "client_id": config.client_id,
                    "code_verifier": _required_string(
                        code_payload,
                        "code_verifier",
                    ),
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
        if token_response.status_code >= 400:
            payload = _error_response_payload(token_response)
            return _oauth_error_poll_result(payload)

        payload = _response_payload(token_response)
        token_set = _token_set_from_payload(payload)
        result = OAuthPollResult(
            status=OAuthPollStatus.CONNECTED,
            token_set=token_set,
            interval_seconds=None,
            message=None,
        )
        return result

    async def refresh_token(
        self,
        provider: LibrarianProvider,
        refresh_token: str,
    ) -> OAuthTokenSet:
        """Refresh an OAuth token through the OpenAI token endpoint.

        Args:
            provider: OPENAI_CODEX provider read model.
            refresh_token: Secret refresh token from encrypted storage.

        Returns:
            OAuthTokenSet: Rotated token values.
        """
        config = _oauth_config(provider.config, self._settings)
        form = {
            "grant_type": _REFRESH_TOKEN_GRANT_TYPE,
            "refresh_token": refresh_token,
            "client_id": config.client_id,
        }
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                config.token_url,
                data=form,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
        if response.status_code >= 400:
            raise UnsupportedProviderError("OAuth token refresh failed")
        payload = _response_payload(response)
        token_set = _token_set_from_payload(payload)
        return token_set


def _oauth_config(
    config: JSONObject,
    settings: OpenAICodexOAuthSettings,
) -> OpenAICodexOAuthConfig:
    issuer = _config_string(config, "issuer", default=settings.issuer).rstrip("/")
    oauth_config = OpenAICodexOAuthConfig(
        device_authorization_url=_config_string(
            config,
            "device_authorization_url",
            default=f"{issuer}{_CODEX_DEVICE_AUTHORIZATION_PATH}",
        ),
        device_token_url=_config_string(
            config,
            "device_token_url",
            default=f"{issuer}{_CODEX_DEVICE_TOKEN_PATH}",
        ),
        token_url=_config_string(
            config,
            "token_url",
            default=f"{issuer}{_CODEX_TOKEN_PATH}",
        ),
        client_id=_config_string(
            config,
            "client_id",
            default=settings.client_id,
        ),
        verification_uri=_config_string(
            config,
            "verification_uri",
            default=f"{issuer}{_CODEX_VERIFICATION_PATH}",
        ),
        redirect_uri=_config_string(
            config,
            "redirect_uri",
            default=f"{issuer}{_CODEX_REDIRECT_PATH}",
        ),
    )
    ensure_openai_codex_oauth_config_is_safe(
        provider_type=ProviderType.OPENAI_CODEX,
        auth_type=AuthType.OAUTH,
        config={
            "device_authorization_url": oauth_config.device_authorization_url,
            "device_token_url": oauth_config.device_token_url,
            "issuer": issuer,
            "redirect_uri": oauth_config.redirect_uri,
            "token_url": oauth_config.token_url,
            "verification_uri": oauth_config.verification_uri,
        },
    )
    return oauth_config


def _config_string(config: JSONObject, key: str, *, default: str) -> str:
    value = config.get(key)
    if value is None:
        return default
    if isinstance(value, str) and value:
        return value
    raise UnsupportedProviderError(f"OAuth config {key} must be a non-empty string")


def _response_payload(response: httpx.Response) -> JSONObject:
    try:
        decoded = loads_json(response.text)
    except ValueError as exc:
        raise UnsupportedProviderError("OAuth provider returned invalid JSON") from exc
    if isinstance(decoded, dict):
        return decoded
    raise UnsupportedProviderError("OAuth provider returned invalid JSON")


def _error_response_payload(response: httpx.Response) -> JSONObject:
    try:
        return _response_payload(response)
    except UnsupportedProviderError:
        return {}


def _pending_poll_result() -> OAuthPollResult:
    return OAuthPollResult(
        status=OAuthPollStatus.PENDING,
        token_set=None,
        interval_seconds=None,
        message="OAuth authorization is pending",
    )


def _slow_down_poll_result() -> OAuthPollResult:
    return OAuthPollResult(
        status=OAuthPollStatus.SLOW_DOWN,
        token_set=None,
        interval_seconds=None,
        message="OAuth polling should slow down",
    )


def _oauth_error_poll_result(payload: JSONObject) -> OAuthPollResult:
    error = _optional_string(payload, "error")
    if error in {"authorization_pending", "pending"}:
        return _pending_poll_result()
    if error == "slow_down":
        return _slow_down_poll_result()
    if error in {"expired_token", "expired"}:
        return OAuthPollResult(
            status=OAuthPollStatus.EXPIRED,
            token_set=None,
            interval_seconds=None,
            message="OAuth device flow expired",
        )
    return OAuthPollResult(
        status=OAuthPollStatus.FAILED,
        token_set=None,
        interval_seconds=None,
        message="OAuth provider rejected the device flow",
    )


def _device_secret_value(*, device_auth_id: str, user_code: str) -> str:
    secret_payload = CodexDeviceSecretPayload(
        device_auth_id=device_auth_id,
        user_code=user_code,
    )
    json_payload: JSONObject = {
        "device_auth_id": secret_payload["device_auth_id"],
        "user_code": secret_payload["user_code"],
    }
    return dumps_json(json_payload).decode("utf-8")


def _device_secret_payload(device_code: str) -> CodexDeviceSecretPayload:
    try:
        decoded = loads_json(device_code)
    except ValueError as exc:
        raise UnsupportedProviderError(
            "OAuth device authorization context is invalid"
        ) from exc
    if not isinstance(decoded, dict):
        raise UnsupportedProviderError("OAuth device authorization context is invalid")
    return CodexDeviceSecretPayload(
        device_auth_id=_required_string(decoded, "device_auth_id"),
        user_code=_required_string(decoded, "user_code"),
    )


def _token_set_from_payload(payload: JSONObject) -> OAuthTokenSet:
    return OAuthTokenSet(
        access_token=_required_string(payload, "access_token"),
        refresh_token=_optional_string(payload, "refresh_token"),
        expires_at=_expires_at_from_payload(payload),
        token_type=_optional_string(payload, "token_type") or "Bearer",
        scope=_optional_string(payload, "scope"),
    )


def _expires_at_from_payload(payload: JSONObject) -> datetime:
    expires_at_value = _optional_string(payload, "expires_at")
    if expires_at_value is not None:
        try:
            parsed = datetime.fromisoformat(expires_at_value.replace("Z", "+00:00"))
        except ValueError as exc:
            raise UnsupportedProviderError("OAuth expires_at is invalid") from exc
        if parsed.tzinfo is None:
            return parsed.replace(tzinfo=UTC)
        return parsed

    expires_in = _optional_int(payload, "expires_in", default=3600)
    return datetime.now(UTC) + timedelta(seconds=expires_in)


def _device_expires_at_from_payload(
    payload: JSONObject,
    settings: OpenAICodexOAuthSettings,
) -> datetime:
    expires_in = _optional_int(
        payload,
        "expires_in",
        default=settings.device_expires_in_seconds,
    )
    return datetime.now(UTC) + timedelta(seconds=expires_in)


def _poll_interval_from_payload(
    payload: JSONObject,
    settings: OpenAICodexOAuthSettings,
) -> int:
    interval = _optional_int(payload, "interval", default=5)
    return max(settings.min_poll_interval_seconds, interval)


def _required_string(payload: JSONObject, key: str) -> str:
    value = payload.get(key)
    if isinstance(value, str) and value:
        return value
    raise UnsupportedProviderError(f"OAuth response missing required field: {key}")


def _optional_string(payload: JSONObject, key: str) -> str | None:
    value = payload.get(key)
    if isinstance(value, str) and value:
        return value
    return None


def _optional_int(payload: JSONObject, key: str, *, default: int) -> int:
    value: JSONValue | None = payload.get(key)
    if isinstance(value, int) and not isinstance(value, bool):
        return value
    return default
