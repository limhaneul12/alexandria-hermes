"""CLI-only library command response schemas."""

from __future__ import annotations

from app.shared.schemas.common_schemas import StrictSchemaModel


class DeletedResourceResult(StrictSchemaModel):
    """JSON output contract for delete-style CLI commands."""

    deleted: str


class FolderEnsureResult(StrictSchemaModel):
    """JSON output contract for path-based folder ensure commands."""

    path: str
    created: list[str]
    existing: list[str]
    folder_id: str


class LibraryListQuery(StrictSchemaModel):
    """Query-string contract for the library list/search CLI command."""

    limit: int
    offset: int
    item_type: str | None = None
    category_id: str | None = None
    q: str | None = None
    content_mode: str | None = None
    search_fields: tuple[str, ...] | None = None
