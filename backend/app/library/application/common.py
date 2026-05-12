"""Shared conversion helpers between ORM and API schemas."""

from __future__ import annotations

from datetime import UTC, datetime

from app.library.domain.entities.read_models import LibraryItem
from app.shared.types.extra_types import JSONValue


def now_utc() -> datetime:
    """Return UTC timestamp for persistence."""
    return datetime.now(UTC)


def item_details_payload(item: LibraryItem) -> dict[str, JSONValue]:
    """Normalize ORM details as dict for response."""
    details = item.details
    if isinstance(details, dict):
        return details
    return {}


def item_to_dict(item: LibraryItem) -> dict[str, JSONValue]:
    """Convert ORM item to API-friendly payload."""
    return {
        "id": item.id,
        "item_type": item.item_type,
        "title": item.title,
        "summary": item.summary,
        "content": item.content,
        "category_id": item.category_id,
        "tags": item.tags,
        "status": item.status,
        "source_type": item.source_type,
        "created_by_type": item.created_by_type,
        "created_by_name": item.created_by_name,
        "details": item_details_payload(item),
        "created_at": item.created_at,
        "updated_at": item.updated_at,
    }
