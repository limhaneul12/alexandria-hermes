"""Map librarian provider read models into typed public payloads."""

from __future__ import annotations

from app.connections.domain.entities.read_models import LibrarianProvider
from app.connections.domain.event_enum.provider_enums import AuthType, ProviderType
from app.connections.domain.types.librarian_provider_payload_types import (
    LibrarianProviderPayload,
)
from app.shared.exceptions import UnsupportedProviderError


def build_provider_payload(model: LibrarianProvider) -> LibrarianProviderPayload:
    """Map provider read model into public payload.

    Args:
        model: Provider read model.

    Returns:
        API payload without secret values.
    """
    if not isinstance(model.provider_type, ProviderType) or not isinstance(
        model.auth_type, AuthType
    ):
        raise UnsupportedProviderError(
            f"Provider type {model.provider_type} is unsupported"
        )
    provider_payload: LibrarianProviderPayload = {
        "id": model.id,
        "name": model.name,
        "provider_type": model.provider_type,
        "auth_type": model.auth_type,
        "enabled": model.enabled,
        "config": dict(model.config),
        "created_at": model.created_at,
        "updated_at": model.updated_at,
    }
    return provider_payload
