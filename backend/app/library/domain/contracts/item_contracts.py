"""Item repository command contracts."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from app.library.domain.event_enum.item_enums import (
    CreatedByType,
    ItemStatus,
    ItemType,
    SourceType,
)
from app.library.domain.types.item_payload_types import (
    ItemCreateRecord,
    ItemUpdateValues,
)
from app.shared.types.extra_types import JSONObject


@dataclass(frozen=True, slots=True, kw_only=True)
class ItemCreate:
    """Fields required to persist a library item."""

    item_type: ItemType
    title: str
    summary: str | None
    content: str
    category_id: str | None
    tags: list[str]
    status: ItemStatus
    source_type: SourceType
    created_by_type: CreatedByType
    created_by_name: str
    details: JSONObject
    created_at: datetime
    updated_at: datetime
    is_archived: bool

    def to_record(self) -> ItemCreateRecord:
        """Return persistence fields for SQLAlchemy model construction.

        Returns:
            ItemCreateRecord: Persistence record for library item creation.
        """
        record: ItemCreateRecord = {
            "item_type": self.item_type.value,
            "title": self.title,
            "summary": self.summary,
            "content": self.content,
            "category_id": self.category_id,
            "tags": self.tags,
            "status": self.status.value,
            "source_type": self.source_type.value,
            "created_by_type": self.created_by_type.value,
            "created_by_name": self.created_by_name,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "details": self.details,
            "is_archived": self.is_archived,
        }
        return record


@dataclass(frozen=True, slots=True, kw_only=True)
class ItemUpdate:
    """Patch fields for a library item."""

    values: ItemUpdateValues

    def to_record(self) -> ItemUpdateValues:
        """Return persistence fields for patching.

        Returns:
            ItemUpdateValues: Value produced by to_record.
        """
        record: ItemUpdateValues = self.values.copy()
        return record
