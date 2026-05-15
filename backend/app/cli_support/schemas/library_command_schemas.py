"""CLI-only library command response schemas."""

from __future__ import annotations

from app.shared.schemas.common_schemas import StrictSchemaModel


class DeletedResourceResult(StrictSchemaModel):
    """JSON output contract for delete-style CLI commands."""

    deleted: str
