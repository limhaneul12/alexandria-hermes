"""CLI-only list query/filter schemas."""

from __future__ import annotations

from app.shared.schemas.common_schemas import StrictSchemaModel


class MemoryCompactListQuery(StrictSchemaModel):
    """Query-string contract for Memory Compact list CLI commands."""

    limit: int
    offset: int
    project: str | None = None
    status: str | None = None


class PromptListFilter(StrictSchemaModel):
    """Local prompt-list filter contract for CLI output shaping."""

    kind: str | None = None
    tag: str | None = None
