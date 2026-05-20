"""Map librarian provider read models into typed public payloads."""

from __future__ import annotations

from datetime import UTC, datetime

from app.connections.domain.entities.read_models import LibrarianProvider
from app.connections.domain.event_enum.provider_enums import AuthType, ProviderType
from app.connections.domain.types.librarian_provider_payload_types import (
    LibrarianProviderPayload,
)
from app.shared.exceptions import (
    BoundaryValidationError,
    ConnectionsProviderUnsupportedError,
)
from app.shared.types.types_convert_utils import enum_value


def _utc_timestamp(value: datetime) -> datetime:
    """Return a timezone-aware UTC timestamp for public provider payloads.

    Args:
        value: Persisted provider timestamp.

    Returns:
        Timezone-aware UTC timestamp.
    """
    if value.tzinfo is None or value.utcoffset() is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def build_provider_payload(model: LibrarianProvider) -> LibrarianProviderPayload:
    """Map provider read model into public payload.

    Args:
        model: Provider read model.

    Returns:
        API payload without secret values.
    """
    try:
        provider_type = enum_value(model.provider_type, ProviderType, "provider_type")
        auth_type = enum_value(model.auth_type, AuthType, "auth_type")
    except BoundaryValidationError as exc:
        raise ConnectionsProviderUnsupportedError(
            f"Provider type {model.provider_type} is unsupported"
        ) from exc
    provider_payload: LibrarianProviderPayload = {
        "id": model.id,
        "name": model.name,
        "provider_type": provider_type,
        "auth_type": auth_type,
        "enabled": model.enabled,
        "config": dict(model.config),
        "created_at": _utc_timestamp(model.created_at),
        "updated_at": _utc_timestamp(model.updated_at),
    }
    return provider_payload
