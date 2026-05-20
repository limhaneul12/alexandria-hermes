"""Credential policy tests for provider OAuth configuration contracts."""

from __future__ import annotations

import pytest
from app.connections.application.librarians.credential_policy import (
    OPENAI_CODEX_OAUTH_ALLOWED_HOSTS,
    OPENAI_CODEX_OAUTH_PROTECTED_CONFIG_KEYS,
    OPENAI_CODEX_OAUTH_URL_KEYS,
    OpenAICodexOAuthAllowedHost,
    OpenAICodexOAuthAllowedPath,
    OpenAICodexOAuthConfigKey,
    ensure_openai_codex_oauth_config_is_safe,
    openai_codex_oauth_allowed_paths_for,
    openai_codex_oauth_config_has_protected_change,
)
from app.connections.domain.event_enum.provider_enums import AuthType, ProviderType
from app.shared.exceptions import ConnectionsProviderUnsupportedError
from app.shared.types.extra_types import JSONObject


def test_openai_codex_oauth_policy_groups_config_keys_as_enums() -> None:
    """OAuth config routing policy should expose typed enum-owned key groups."""

    assert OPENAI_CODEX_OAUTH_URL_KEYS == (
        OpenAICodexOAuthConfigKey.DEVICE_AUTHORIZATION_URL,
        OpenAICodexOAuthConfigKey.DEVICE_TOKEN_URL,
        OpenAICodexOAuthConfigKey.ISSUER,
        OpenAICodexOAuthConfigKey.REDIRECT_URI,
        OpenAICodexOAuthConfigKey.TOKEN_URL,
        OpenAICodexOAuthConfigKey.VERIFICATION_URI,
    )
    assert OPENAI_CODEX_OAUTH_PROTECTED_CONFIG_KEYS == (
        OpenAICodexOAuthConfigKey.DEVICE_AUTHORIZATION_URL,
        OpenAICodexOAuthConfigKey.DEVICE_TOKEN_URL,
        OpenAICodexOAuthConfigKey.CLIENT_ID,
        OpenAICodexOAuthConfigKey.ISSUER,
        OpenAICodexOAuthConfigKey.REDIRECT_URI,
        OpenAICodexOAuthConfigKey.SCOPE,
        OpenAICodexOAuthConfigKey.TOKEN_URL,
        OpenAICodexOAuthConfigKey.VERIFICATION_URI,
    )


def test_openai_codex_oauth_policy_groups_allowed_endpoint_parts_as_enums() -> None:
    """Allowed OpenAI Codex OAuth endpoints should be enum-owned contracts."""

    assert (
        frozenset({OpenAICodexOAuthAllowedHost.AUTH_OPENAI})
        == OPENAI_CODEX_OAUTH_ALLOWED_HOSTS
    )
    assert openai_codex_oauth_allowed_paths_for(
        OpenAICodexOAuthConfigKey.DEVICE_AUTHORIZATION_URL
    ) == frozenset({OpenAICodexOAuthAllowedPath.DEVICE_AUTHORIZATION})
    assert openai_codex_oauth_allowed_paths_for(
        OpenAICodexOAuthConfigKey.ISSUER
    ) == frozenset(
        {
            OpenAICodexOAuthAllowedPath.EMPTY,
            OpenAICodexOAuthAllowedPath.ROOT,
        }
    )


def test_openai_codex_oauth_policy_keeps_existing_safety_behavior() -> None:
    """Enum-backed policy should still validate routing fields and protected changes."""

    safe_config: JSONObject = {
        "device_authorization_url": "https://auth.openai.com/api/accounts/deviceauth/usercode",
        "device_token_url": "https://auth.openai.com/api/accounts/deviceauth/token",
        "issuer": "https://auth.openai.com/",
        "redirect_uri": "https://auth.openai.com/deviceauth/callback",
        "token_url": "https://auth.openai.com/oauth/token",
        "verification_uri": "https://auth.openai.com/codex/device",
        "client_id": "codex-client",
        "scope": "openid profile email",
    }

    ensure_openai_codex_oauth_config_is_safe(
        provider_type=ProviderType.OPENAI_CODEX,
        auth_type=AuthType.OAUTH,
        config=safe_config,
    )
    assert not openai_codex_oauth_config_has_protected_change(safe_config, safe_config)

    unsafe_config = dict(safe_config)
    unsafe_config["device_token_url"] = (
        "https://example.com/api/accounts/deviceauth/token"
    )
    with pytest.raises(ConnectionsProviderUnsupportedError) as exc_info:
        ensure_openai_codex_oauth_config_is_safe(
            provider_type=ProviderType.OPENAI_CODEX,
            auth_type=AuthType.OAUTH,
            config=unsafe_config,
        )

    assert str(exc_info.value) == (
        "OAuth config device_token_url host is not approved for OPENAI_CODEX"
    )
    assert openai_codex_oauth_config_has_protected_change(safe_config, unsafe_config)
