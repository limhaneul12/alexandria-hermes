"""CLI-only Context Vault response schemas."""

from __future__ import annotations

from enum import StrEnum

from app.shared.schemas.common_schemas import StrictSchemaModel


class LocalContextCommandStatus(StrEnum):
    """Statuses emitted by local-only context command adapters."""

    NOT_AVAILABLE = "NOT_AVAILABLE"


class UnsupportedContextOperationResult(StrictSchemaModel):
    """Payload printed when a context command is intentionally unavailable."""

    status: LocalContextCommandStatus
    reason: str
    context_id: str | None = None
