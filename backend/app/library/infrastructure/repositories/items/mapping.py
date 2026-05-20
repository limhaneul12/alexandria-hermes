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
from app.shared.types.types_convert_utils import aware_utc_datetime


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
        tags=row.tags,
        status=ItemStatus(row.status),
        source_type=SourceType(row.source_type),
        created_by_type=CreatedByType(row.created_by_type),
        created_by_name=row.created_by_name,
        details=row.details,
        created_at=aware_utc_datetime(row.created_at),
        updated_at=aware_utc_datetime(row.updated_at),
        is_archived=row.is_archived,
    )
    return item
