"""Provider credential persistence contracts."""

from __future__ import annotations

from app.connections.infrastructure.models.librarian_provider_models import (
    ProviderSecretORM,
)
from sqlalchemy import Text


def test_provider_credential_value_uses_unbounded_text_storage() -> None:
    """Encrypted OAuth payloads must not be truncated by a VARCHAR limit."""
    value_type = ProviderSecretORM.__table__.c.value.type

    assert isinstance(value_type, Text)
