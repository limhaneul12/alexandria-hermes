"""Pydantic schemas for thin library candidate search."""

from __future__ import annotations

from datetime import datetime

from app.library.domain.event_enum.item_enums import ItemStatus, ItemType
from app.shared.schemas.common_schemas import StrictSchemaModel
from app.shared.types.extra_types import JSONValue
from pydantic import Field


class ItemSearchHitResponse(StrictSchemaModel):
    """Candidate search hit without full content."""

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
    details_preview: dict[str, JSONValue]
    content_char_count: int = Field(ge=0)
    updated_at: datetime


class ItemSearchResponse(StrictSchemaModel):
    """Paginated thin candidate search response."""

    items: list[ItemSearchHitResponse]
    total: int = Field(ge=0)
    limit: int = Field(ge=1, le=100)
    offset: int = Field(ge=0)
