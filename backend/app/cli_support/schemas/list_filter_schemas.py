"""CLI-only list filter payload schemas."""

from __future__ import annotations

from app.shared.schemas.common_schemas import StrictSchemaModel


class MemoryCompactListQuery(StrictSchemaModel):
    """Query parameters for Memory Compact listing."""

    limit: int
    offset: int
    project: str | None = None
    status: str | None = None
