"""Librarian provider concept enum definitions."""

from __future__ import annotations

from enum import StrEnum


class ProviderType(StrEnum):
    """Librarian provider implementation type."""

    OPENAI = "OPENAI"
    OPENAI_CODEX = "OPENAI_CODEX"
    MINIO = "MINIO"


class AuthType(StrEnum):
    """Authentication mode used by a librarian provider."""

    API_KEY = "API_KEY"
    OAUTH = "OAUTH"
    NONE = "NONE"


class OAuthPollStatus(StrEnum):
    """OAuth device-flow poll outcome."""

    PENDING = "pending"
    SLOW_DOWN = "slow_down"
    CONNECTED = "connected"
    EXPIRED = "expired"
    FAILED = "failed"


class OAuthConnectionStatus(StrEnum):
    """Public OAuth connection state."""

    NOT_CONNECTED = "not_connected"
    PENDING = "pending"
    CONNECTED = "connected"
    REFRESH_REQUIRED = "refresh_required"
    MISSING_REFRESH_TOKEN = "missing_refresh_token"
    EXPIRED = "expired"
    FAILED = "failed"


class ProviderSecretKey(StrEnum):
    """Secret-store key names owned by librarian provider credentials."""

    API_KEY = "api_key"
    OAUTH_ACCESS_TOKEN = "oauth_access_token"
    OAUTH_REFRESH_TOKEN = "oauth_refresh_token"
    OAUTH_EXPIRES_AT = "oauth_expires_at"
    OAUTH_TOKEN_TYPE = "oauth_token_type"
    OAUTH_SCOPE = "oauth_scope"
    OAUTH_DEVICE_CODE = "oauth_device_code"
    OAUTH_DEVICE_EXPIRES_AT = "oauth_device_expires_at"
    OAUTH_POLL_INTERVAL_SECONDS = "oauth_poll_interval_seconds"


class ConfigCredentialKey(StrEnum):
    """Credential-shaped config keys forbidden in public provider config."""

    API_KEY = "api_key"
    OAUTH_ACCESS_TOKEN = "oauth_access_token"
    OAUTH_REFRESH_TOKEN = "oauth_refresh_token"
    OAUTH_EXPIRES_AT = "oauth_expires_at"
    OAUTH_TOKEN_TYPE = "oauth_token_type"
    OAUTH_SCOPE = "oauth_scope"
    OAUTH_DEVICE_CODE = "oauth_device_code"
    OAUTH_DEVICE_EXPIRES_AT = "oauth_device_expires_at"
    OAUTH_POLL_INTERVAL_SECONDS = "oauth_poll_interval_seconds"
    ACCESS_TOKEN = "access_token"
    REFRESH_TOKEN = "refresh_token"
    CLIENT_SECRET = "client_secret"
    DEVICE_CODE = "device_code"
    USER_CODE = "user_code"
    TOKEN = "token"
    SECRET = "secret"
    PASSWORD = "password"
