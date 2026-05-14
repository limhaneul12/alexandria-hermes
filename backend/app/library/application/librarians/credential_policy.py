"""Pure credential policy checks for librarian providers."""

from __future__ import annotations

from app.library.domain.event_enum.provider_enums import AuthType, ConfigCredentialKey
from app.shared.exceptions import UnsupportedProviderError
from app.shared.types.extra_types import JSONObject, JSONValue


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


def ensure_create_credentials_are_present(
    auth_type: AuthType,
    api_key: str | None,
    oauth_access_token: str | None,
) -> None:
    """Validate credentials required for provider creation.

    Args:
        auth_type: Requested authentication mode.
        api_key: Optional API key credential.
        oauth_access_token: Optional OAuth access token.

    Returns:
        None.

    Raises:
        UnsupportedProviderError: When required credentials are absent.
    """
    if auth_type is AuthType.API_KEY and not api_key:
        raise UnsupportedProviderError("API_KEY auth requires api_key")
    if auth_type is AuthType.OAUTH and not oauth_access_token:
        raise UnsupportedProviderError("OAUTH auth requires oauth_access_token")


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
