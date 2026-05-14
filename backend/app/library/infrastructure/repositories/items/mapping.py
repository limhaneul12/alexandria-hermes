"""Mapping helpers for library item repository rows."""

from __future__ import annotations

from app.library.domain.entities.read_models import LibraryItem
from app.library.domain.event_enum.item_enums import (
    CreatedByType,
    ItemStatus,
    ItemType,
    SourceType,
)
from app.library.infrastructure.models.item_models import LibraryItemORM
from app.shared.types.extra_types import JSONValue


def details_from_row(row: LibraryItemORM) -> dict[str, JSONValue]:
    """Return a typed details dictionary from an ORM row.

    Args:
        row [LibraryItemORM]: Value supplied to details_from_row.

    Returns:
        dict[str, JSONValue]: Value produced by details_from_row.
    """
    details = row.details
    item_details = details if isinstance(details, dict) else {}
    return item_details


def tags_from_row(row: LibraryItemORM) -> list[str]:
    """Return a typed tags list from an ORM row.

    Args:
        row [LibraryItemORM]: Value supplied to tags_from_row.

    Returns:
        list[str]: Value produced by tags_from_row.
    """
    tags = row.tags
    item_tags = tags if isinstance(tags, list) else []
    return item_tags


def map_item_row_to_read_model(row: LibraryItemORM) -> LibraryItem:
    """Map an item ORM row into the domain read model.

    Args:
        row [LibraryItemORM]: Value supplied to map_item_row_to_read_model.

    Returns:
        LibraryItem: Value produced by map_item_row_to_read_model.
    """
    item = LibraryItem(
        id=row.id,
        item_type=ItemType(row.item_type),
        title=row.title,
        summary=row.summary,
        content=row.content,
        category_id=row.category_id,
        tags=tags_from_row(row),
        status=ItemStatus(row.status),
        source_type=SourceType(row.source_type),
        created_by_type=CreatedByType(row.created_by_type),
        created_by_name=row.created_by_name,
        details=details_from_row(row),
        created_at=row.created_at,
        updated_at=row.updated_at,
        is_archived=row.is_archived,
    )
    return item
