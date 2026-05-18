"""Provider credential policy enum definitions."""

from __future__ import annotations

from enum import StrEnum


class OpenAICodexOAuthConfigKey(StrEnum):
    """Public OpenAI Codex OAuth config keys that affect token routing."""

    DEVICE_AUTHORIZATION_URL = "device_authorization_url"
    DEVICE_TOKEN_URL = "device_token_url"
    CLIENT_ID = "client_id"
    ISSUER = "issuer"
    REDIRECT_URI = "redirect_uri"
    SCOPE = "scope"
    TOKEN_URL = "token_url"
    VERIFICATION_URI = "verification_uri"


class OpenAICodexOAuthAllowedHost(StrEnum):
    """Approved hostnames for OpenAI Codex OAuth endpoint config."""

    AUTH_OPENAI = "auth.openai.com"


class OpenAICodexOAuthAllowedPath(StrEnum):
    """Approved URL paths for OpenAI Codex OAuth endpoint config."""

    EMPTY = ""
    ROOT = "/"
    DEVICE_AUTHORIZATION = "/api/accounts/deviceauth/usercode"
    DEVICE_TOKEN = "/api/accounts/deviceauth/token"
    DEVICE_CALLBACK = "/deviceauth/callback"
    OAUTH_TOKEN = "/oauth/token"
    CODEX_DEVICE = "/codex/device"
