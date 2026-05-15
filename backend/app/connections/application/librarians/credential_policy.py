"""Pure credential policy checks for librarian providers."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Final
from urllib.parse import urlparse

from app.connections.domain.event_enum.provider_enums import (
    AuthType,
    ConfigCredentialKey,
    ProviderType,
)
from app.shared.exceptions import UnsupportedProviderError
from app.shared.types.extra_types import JSONObject, JSONValue

SUPPORTED_PROVIDER_AUTH_TYPES: Final[Mapping[ProviderType, frozenset[AuthType]]] = {
    ProviderType.OPENAI: frozenset({AuthType.API_KEY}),
    ProviderType.OPENAI_CODEX: frozenset({AuthType.OAUTH}),
    ProviderType.MINIO: frozenset({AuthType.API_KEY}),
}
OPENAI_CODEX_OAUTH_URL_KEYS: Final[tuple[str, ...]] = (
    "device_authorization_url",
    "device_token_url",
    "issuer",
    "redirect_uri",
    "token_url",
    "verification_uri",
)
OPENAI_CODEX_OAUTH_PROTECTED_CONFIG_KEYS: Final[tuple[str, ...]] = (
    "device_authorization_url",
    "device_token_url",
    "client_id",
    "issuer",
    "redirect_uri",
    "scope",
    "token_url",
    "verification_uri",
)
_OPENAI_CODEX_OAUTH_ALLOWED_HOSTS: Final[frozenset[str]] = frozenset(
    {
        "auth.openai.com",
    }
)
_OPENAI_CODEX_OAUTH_ALLOWED_PATHS: Final[Mapping[str, frozenset[str]]] = {
    "device_authorization_url": frozenset({"/api/accounts/deviceauth/usercode"}),
    "device_token_url": frozenset({"/api/accounts/deviceauth/token"}),
    "issuer": frozenset({"", "/"}),
    "redirect_uri": frozenset({"/deviceauth/callback"}),
    "token_url": frozenset({"/oauth/token"}),
    "verification_uri": frozenset({"/codex/device"}),
}


def ensure_provider_config_has_no_credentials(config: JSONObject) -> None:
    """Reject credentials embedded in provider config payloads.

    Args:
        config: Public provider configuration payload.

    Returns:
        None.

    Raises:
        UnsupportedProviderError: When config includes credential-shaped keys.
    """
    if _config_contains_credential_key(config):
        raise UnsupportedProviderError(
            "Provider config must not include credential fields"
        )


def ensure_provider_auth_type_is_supported(
    provider_type: ProviderType,
    auth_type: AuthType,
) -> None:
    """Validate provider/auth compatibility before checking credential material.

    Args:
        provider_type: Provider implementation family.
        auth_type: Requested authentication mode.

    Return:
        None.

    Raises:
        UnsupportedProviderError: When the provider/auth combination is invalid.
    """
    supported_auth_types = SUPPORTED_PROVIDER_AUTH_TYPES[provider_type]
    if auth_type not in supported_auth_types:
        raise UnsupportedProviderError(
            f"Provider type {provider_type.value} does not support {auth_type.value} auth"
        )


def ensure_create_credentials_are_present(
    provider_type: ProviderType,
    auth_type: AuthType,
    api_key: str | None,
    oauth_access_token: str | None,
) -> None:
    """Validate credentials required for provider creation.

    Args:
        provider_type: Provider implementation family.
        auth_type: Requested authentication mode.
        api_key: Optional API key credential.
        oauth_access_token: Optional OAuth access token.

    Returns:
        None.

    Raises:
        UnsupportedProviderError: When required credentials are absent.
    """
    ensure_provider_auth_type_is_supported(
        provider_type=provider_type,
        auth_type=auth_type,
    )
    if auth_type is AuthType.API_KEY and not api_key:
        raise UnsupportedProviderError("API_KEY auth requires api_key")


def ensure_openai_codex_oauth_config_is_safe(
    provider_type: ProviderType,
    auth_type: AuthType,
    config: JSONObject,
) -> None:
    """Validate mutable OAuth endpoint config cannot become an SSRF sink.

    Args:
        provider_type: Provider implementation family.
        auth_type: Requested authentication mode.
        config: Public provider config payload.

    Returns:
        None.

    Raises:
        UnsupportedProviderError: When OAuth endpoints are unsafe.
    """
    if (
        provider_type is not ProviderType.OPENAI_CODEX
        or auth_type is not AuthType.OAUTH
    ):
        return

    for key in OPENAI_CODEX_OAUTH_URL_KEYS:
        value = config.get(key)
        if value is None:
            continue
        if not isinstance(value, str) or not value:
            raise UnsupportedProviderError(f"OAuth config {key} must be a URL string")
        _ensure_https_allowed_host(key, value)


def openai_codex_oauth_config_has_protected_change(
    previous_config: JSONObject,
    next_config: JSONObject,
) -> bool:
    """Return whether token-routing OAuth config changed.

    Args:
        previous_config: Current persisted public provider config.
        next_config: Requested replacement public provider config.

    Returns:
        bool: True when protected OAuth routing fields changed.
    """
    for key in OPENAI_CODEX_OAUTH_PROTECTED_CONFIG_KEYS:
        if _config_text_value(previous_config, key) != _config_text_value(
            next_config,
            key,
        ):
            return True
    return False


def _config_contains_credential_key(value: JSONValue) -> bool:
    if isinstance(value, dict):
        for key, nested in value.items():
            if _is_config_credential_key(_normalized_config_key(key)):
                return True
            if _config_contains_credential_key(nested):
                return True
        return False
    if isinstance(value, list):
        contains_credential = any(
            _config_contains_credential_key(item) for item in value
        )
        return contains_credential
    return False


def _is_config_credential_key(key: str) -> bool:
    try:
        ConfigCredentialKey(key)
    except ValueError:
        return False
    return True


def _normalized_config_key(key: str) -> str:
    normalized_key = key.strip().lower().replace("-", "_")
    return normalized_key


def _ensure_https_allowed_host(key: str, url: str) -> None:
    parsed = urlparse(url)
    hostname = parsed.hostname
    if parsed.scheme != "https" or hostname is None:
        raise UnsupportedProviderError(
            f"OAuth config {key} must use an approved HTTPS endpoint"
        )
    if parsed.username is not None or parsed.password is not None:
        raise UnsupportedProviderError(f"OAuth config {key} must not include userinfo")
    if parsed.port is not None and parsed.port != 443:
        raise UnsupportedProviderError(
            f"OAuth config {key} must not include a custom port"
        )
    if hostname.lower() not in _OPENAI_CODEX_OAUTH_ALLOWED_HOSTS:
        raise UnsupportedProviderError(
            f"OAuth config {key} host is not approved for OPENAI_CODEX"
        )
    approved_paths = _OPENAI_CODEX_OAUTH_ALLOWED_PATHS[key]
    if (
        parsed.path not in approved_paths
        or parsed.params
        or parsed.query
        or parsed.fragment
    ):
        raise UnsupportedProviderError(
            f"OAuth config {key} path is not approved for OPENAI_CODEX"
        )


def _config_text_value(config: JSONObject, key: str) -> str | None:
    value = config.get(key)
    if isinstance(value, str):
        return value
    return None
