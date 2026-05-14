"""Librarian provider concept enum definitions."""

from __future__ import annotations

from enum import StrEnum


class ProviderType(StrEnum):
    """Librarian provider implementation type."""

    OPENAI = "OPENAI"
    MINIO = "MINIO"


class AuthType(StrEnum):
    """Authentication mode used by a librarian provider."""

    API_KEY = "API_KEY"
    OAUTH = "OAUTH"
    NONE = "NONE"


class ConfigCredentialKey(StrEnum):
    """Credential-shaped config keys forbidden in public provider config."""

    API_KEY = "api_key"
    OAUTH_ACCESS_TOKEN = "oauth_access_token"
    ACCESS_TOKEN = "access_token"
    REFRESH_TOKEN = "refresh_token"
    TOKEN = "token"
    SECRET = "secret"
    PASSWORD = "password"
