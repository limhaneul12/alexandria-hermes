"""Provider enum parsing for librarian client factory orchestration."""

from __future__ import annotations

from app.connections.domain.event_enum.provider_enums import AuthType, ProviderType

SUPPORTED_SDK_PROVIDER_TYPES = frozenset({ProviderType.OPENAI, ProviderType.MINIO})


def parse_provider_type(value: ProviderType | str) -> ProviderType | None:
    """Parse provider type while preserving stale unsupported rows as absent.

    Args:
        value: Persisted provider type value.

    Returns:
        ProviderType | None: Supported provider type, otherwise ``None``.
    """
    if isinstance(value, ProviderType):
        return value
    try:
        return ProviderType(value)
    except ValueError:
        return None


def parse_auth_type(value: AuthType | str) -> AuthType:
    """Parse auth type with a clear unsupported fallback.

    Args:
        value: Persisted auth type value.

    Returns:
        AuthType: Parsed auth type or ``AuthType.NONE`` for stale values.
    """
    if isinstance(value, AuthType):
        return value
    return AuthType(value)
