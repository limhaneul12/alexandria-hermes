"""Domain-owned payload contracts for thin item search."""

from __future__ import annotations

from datetime import datetime

from app.library.domain.event_enum.item_enums import ItemStatus, ItemType
from app.shared.types.extra_types import JSONObject
from typing_extensions import TypedDict


class ItemSearchHitPayload(TypedDict, closed=True):
    """Candidate payload for broad library search results."""

    id: str
    item_type: ItemType
    title: str
    summary: str | None
    tags: list[str]
    status: ItemStatus
    category_id: str | None
    score: float
    why_matched: list[str]
    highlights: list[str]
    details_preview: JSONObject
    content_char_count: int
    updated_at: datetime


class ItemSearchResultPayload(TypedDict, closed=True):
    """Paginated candidate search result payload."""

    items: list[ItemSearchHitPayload]
    total: int
    limit: int
    offset: int
