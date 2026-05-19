"""Pure credential policy checks for librarian providers."""

from __future__ import annotations

from collections.abc import Mapping
from typing import ClassVar
from urllib.parse import urlparse

from app.connections.domain.event_enum.credential_policy_enums import (
    OpenAICodexOAuthAllowedHost,
    OpenAICodexOAuthAllowedPath,
    OpenAICodexOAuthConfigKey,
)
from app.connections.domain.event_enum.provider_enums import (
    AuthType,
    ConfigCredentialKey,
    ProviderType,
)
from app.shared.exceptions import UnsupportedProviderError
from app.shared.types.extra_types import JSONObject, JSONValue


class ProviderAuthPolicy:
    """Provider/auth compatibility policy for librarian credentials."""

    _SUPPORTED_AUTH_TYPES: ClassVar[Mapping[ProviderType, frozenset[AuthType]]] = {
        ProviderType.OPENAI: frozenset({AuthType.API_KEY}),
        ProviderType.OPENAI_CODEX: frozenset({AuthType.OAUTH}),
    }

    @classmethod
    def supported_auth_types(cls, provider_type: ProviderType) -> frozenset[AuthType]:
        """Return auth modes supported by a provider type.

        Args:
            provider_type: Provider implementation family.

        Returns:
            frozenset[AuthType]: Supported auth modes for the provider type.
        """
        supported_auth_types = cls._SUPPORTED_AUTH_TYPES[provider_type]
        return supported_auth_types

    @classmethod
    def ensure_supported(
        cls,
        provider_type: ProviderType,
        auth_type: AuthType,
    ) -> None:
        """Validate provider/auth compatibility.

        Args:
            provider_type: Provider implementation family.
            auth_type: Requested authentication mode.

        Returns:
            None.

        Raises:
            UnsupportedProviderError: When the provider/auth combination is invalid.
        """
        if auth_type not in cls.supported_auth_types(provider_type):
            raise UnsupportedProviderError(
                f"Provider type {provider_type.value} does not support {auth_type.value} auth"
            )


class OpenAICodexOAuthPolicy:
    """Endpoint and protected-field policy for OpenAI Codex OAuth config."""

    _URL_KEYS: ClassVar[tuple[OpenAICodexOAuthConfigKey, ...]] = (
        OpenAICodexOAuthConfigKey.DEVICE_AUTHORIZATION_URL,
        OpenAICodexOAuthConfigKey.DEVICE_TOKEN_URL,
        OpenAICodexOAuthConfigKey.ISSUER,
        OpenAICodexOAuthConfigKey.REDIRECT_URI,
        OpenAICodexOAuthConfigKey.TOKEN_URL,
        OpenAICodexOAuthConfigKey.VERIFICATION_URI,
    )
    _PROTECTED_CONFIG_KEYS: ClassVar[tuple[OpenAICodexOAuthConfigKey, ...]] = (
        OpenAICodexOAuthConfigKey.DEVICE_AUTHORIZATION_URL,
        OpenAICodexOAuthConfigKey.DEVICE_TOKEN_URL,
        OpenAICodexOAuthConfigKey.CLIENT_ID,
        OpenAICodexOAuthConfigKey.ISSUER,
        OpenAICodexOAuthConfigKey.REDIRECT_URI,
        OpenAICodexOAuthConfigKey.SCOPE,
        OpenAICodexOAuthConfigKey.TOKEN_URL,
        OpenAICodexOAuthConfigKey.VERIFICATION_URI,
    )
    _ALLOWED_HOSTS: ClassVar[frozenset[OpenAICodexOAuthAllowedHost]] = frozenset(
        {OpenAICodexOAuthAllowedHost.AUTH_OPENAI}
    )
    _ALLOWED_PATHS: ClassVar[
        Mapping[OpenAICodexOAuthConfigKey, frozenset[OpenAICodexOAuthAllowedPath]]
    ] = {
        OpenAICodexOAuthConfigKey.DEVICE_AUTHORIZATION_URL: frozenset(
            {OpenAICodexOAuthAllowedPath.DEVICE_AUTHORIZATION}
        ),
        OpenAICodexOAuthConfigKey.DEVICE_TOKEN_URL: frozenset(
            {OpenAICodexOAuthAllowedPath.DEVICE_TOKEN}
        ),
        OpenAICodexOAuthConfigKey.ISSUER: frozenset(
            {OpenAICodexOAuthAllowedPath.EMPTY, OpenAICodexOAuthAllowedPath.ROOT}
        ),
        OpenAICodexOAuthConfigKey.REDIRECT_URI: frozenset(
            {OpenAICodexOAuthAllowedPath.DEVICE_CALLBACK}
        ),
        OpenAICodexOAuthConfigKey.TOKEN_URL: frozenset(
            {OpenAICodexOAuthAllowedPath.OAUTH_TOKEN}
        ),
        OpenAICodexOAuthConfigKey.VERIFICATION_URI: frozenset(
            {OpenAICodexOAuthAllowedPath.CODEX_DEVICE}
        ),
    }

    @classmethod
    def url_keys(cls) -> tuple[OpenAICodexOAuthConfigKey, ...]:
        """Return config keys whose values must be approved HTTPS URLs.

        Returns:
            tuple[OpenAICodexOAuthConfigKey, ...]: URL-bearing config keys.
        """
        return cls._URL_KEYS

    @classmethod
    def protected_config_keys(cls) -> tuple[OpenAICodexOAuthConfigKey, ...]:
        """Return config keys that affect OAuth token routing.

        Returns:
            tuple[OpenAICodexOAuthConfigKey, ...]: Protected config keys.
        """
        return cls._PROTECTED_CONFIG_KEYS

    @classmethod
    def allowed_hosts(cls) -> frozenset[OpenAICodexOAuthAllowedHost]:
        """Return approved OpenAI Codex OAuth hostnames.

        Returns:
            frozenset[OpenAICodexOAuthAllowedHost]: Approved hostnames.
        """
        return cls._ALLOWED_HOSTS

    @classmethod
    def allowed_paths_for(
        cls,
        key: OpenAICodexOAuthConfigKey,
    ) -> frozenset[OpenAICodexOAuthAllowedPath]:
        """Return approved URL paths for a config key.

        Args:
            key: OAuth config key.

        Returns:
            frozenset[OpenAICodexOAuthAllowedPath]: Approved paths for the key.
        """
        return cls._ALLOWED_PATHS[key]

    @classmethod
    def ensure_config_is_safe(cls, config: JSONObject) -> None:
        """Validate mutable OAuth endpoint config cannot become an SSRF sink.

        Args:
            config: Public provider config payload.

        Returns:
            None.

        Raises:
            UnsupportedProviderError: When OAuth endpoints are unsafe.
        """
        for key in cls.url_keys():
            value = config.get(key.value)
            if value is None:
                continue
            if not isinstance(value, str) or not value:
                raise UnsupportedProviderError(
                    f"OAuth config {key.value} must be a URL string"
                )
            cls._ensure_https_allowed_host(key, value)

    @classmethod
    def has_protected_change(
        cls,
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
        for key in cls.protected_config_keys():
            if _config_text_value(previous_config, key.value) != _config_text_value(
                next_config,
                key.value,
            ):
                return True
        return False

    @classmethod
    def _ensure_https_allowed_host(
        cls,
        key: OpenAICodexOAuthConfigKey,
        url: str,
    ) -> None:
        parsed = urlparse(url)
        hostname = parsed.hostname
        if parsed.scheme != "https" or hostname is None:
            raise UnsupportedProviderError(
                f"OAuth config {key.value} must use an approved HTTPS endpoint"
            )
        if parsed.username is not None or parsed.password is not None:
            raise UnsupportedProviderError(
                f"OAuth config {key.value} must not include userinfo"
            )
        if parsed.port is not None and parsed.port != 443:
            raise UnsupportedProviderError(
                f"OAuth config {key.value} must not include a custom port"
            )
        if hostname.lower() not in cls._allowed_host_values():
            raise UnsupportedProviderError(
                f"OAuth config {key.value} host is not approved for OPENAI_CODEX"
            )
        if (
            parsed.path not in cls._allowed_path_values_for(key)
            or parsed.params
            or parsed.query
            or parsed.fragment
        ):
            raise UnsupportedProviderError(
                f"OAuth config {key.value} path is not approved for OPENAI_CODEX"
            )

    @classmethod
    def _allowed_host_values(cls) -> frozenset[str]:
        allowed_host_values = frozenset(host.value for host in cls.allowed_hosts())
        return allowed_host_values

    @classmethod
    def _allowed_path_values_for(cls, key: OpenAICodexOAuthConfigKey) -> frozenset[str]:
        allowed_path_values = frozenset(
            path.value for path in cls.allowed_paths_for(key)
        )
        return allowed_path_values


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
    ProviderAuthPolicy.ensure_supported(
        provider_type=provider_type,
        auth_type=auth_type,
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

    OpenAICodexOAuthPolicy.ensure_config_is_safe(config)


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
    return OpenAICodexOAuthPolicy.has_protected_change(
        previous_config=previous_config,
        next_config=next_config,
    )


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


def _config_text_value(config: JSONObject, key: str) -> str | None:
    value = config.get(key)
    if isinstance(value, str):
        return value
    return None
