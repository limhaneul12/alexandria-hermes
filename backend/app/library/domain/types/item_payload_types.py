"""Domain-owned item payload type contracts."""

from __future__ import annotations

from datetime import datetime

from app.library.domain.event_enum.item_enums import (
    CreatedByType,
    ItemStatus,
    ItemType,
    SourceType,
)
from app.shared.types.extra_types import JSONObject
from typing_extensions import TypedDict


class LibraryItemPayload(TypedDict, closed=True):
    """Shaped public payload for a library item read model."""

    id: str
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


class ItemCreateRecord(TypedDict, closed=True):
    """Persistence record for creating a library item."""

    item_type: str
    title: str
    summary: str | None
    content: str
    category_id: str | None
    tags: list[str]
    status: str
    source_type: str
    created_by_type: str
    created_by_name: str
    created_at: datetime
    updated_at: datetime
    details: JSONObject
    is_archived: bool


class ItemUpdateValues(TypedDict, total=False, closed=True):
    """Explicit patchable library item fields."""

    title: str
    summary: str | None
    content: str
    category_id: str | None
    tags: list[str]
    status: ItemStatus
    details: JSONObject


type ItemUpdateRecord = ItemUpdateValues
type LibraryItemPayloadList = list[LibraryItemPayload]
type LibraryItemListResult = tuple[LibraryItemPayloadList, int]
