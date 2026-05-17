"""Pydantic schemas for thin library candidate search."""

from __future__ import annotations

from datetime import datetime

from app.library.domain.event_enum.item_enums import ItemStatus, ItemType
from app.shared.schemas.common_schemas import StrictSchemaModel
from app.shared.types.extra_types import JSONValue
from pydantic import Field, field_validator


def _item_type(value: ItemType | str) -> ItemType:
    if isinstance(value, ItemType):
        return value
    return ItemType(value)


def _item_status(value: ItemStatus | str) -> ItemStatus:
    if isinstance(value, ItemStatus):
        return value
    return ItemStatus(value)


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

    @field_validator("item_type", mode="before")
    @classmethod
    def parse_item_type(cls, value: ItemType | str) -> ItemType:
        """Parse item type values.

        Args:
            value: Enum member or string value.

        Returns:
            Parsed item type.
        """
        return _item_type(value)

    @field_validator("status", mode="before")
    @classmethod
    def parse_status(cls, value: ItemStatus | str) -> ItemStatus:
        """Parse status values.

        Args:
            value: Enum member or string value.

        Returns:
            Parsed item status.
        """
        return _item_status(value)


class ItemSearchResponse(StrictSchemaModel):
    """Paginated thin candidate search response."""

    items: list[ItemSearchHitResponse]
    total: int = Field(ge=0)
    limit: int = Field(ge=1, le=100)
    offset: int = Field(ge=0)
