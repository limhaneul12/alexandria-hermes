"""Shared schemas for generic item endpoints."""

from __future__ import annotations

from datetime import datetime

from app.library.domain.event_enum.item_enums import (
    CreatedByType,
    ItemStatus,
    ItemType,
    SourceType,
)
from app.library.interface.schemas._types import StrictRootSchema, StrictSchema
from app.shared.types.extra_types import JSONValue
from pydantic import ConfigDict, Field, field_validator


# Broad type justified: Pydantic before validators receive raw boundary input before contract validation.
def _item_type(value: object) -> ItemType:
    """Accept public JSON item type values at API boundaries."""
    if isinstance(value, ItemType):
        return value
    if isinstance(value, str):
        return ItemType(value)
    raise ValueError("item_type must be a valid item type")


# Broad type justified: Pydantic before validators receive raw boundary input before contract validation.
def _item_status(value: object) -> ItemStatus:
    """Accept public JSON item status values at API boundaries."""
    if isinstance(value, ItemStatus):
        return value
    if isinstance(value, str):
        return ItemStatus(value)
    raise ValueError("status must be a valid item status")


# Broad type justified: Pydantic before validators receive raw boundary input before contract validation.
def _source_type(value: object) -> SourceType:
    """Accept public JSON source type values at API boundaries."""
    if isinstance(value, SourceType):
        return value
    if isinstance(value, str):
        return SourceType(value)
    raise ValueError("source_type must be a valid source type")


# Broad type justified: Pydantic before validators receive raw boundary input before contract validation.
def _created_by_type(value: object) -> CreatedByType:
    """Accept public JSON creator type values at API boundaries."""
    if isinstance(value, CreatedByType):
        return value
    if isinstance(value, str):
        return CreatedByType(value)
    raise ValueError("created_by_type must be a valid creator type")


class ItemCreateRequest(StrictSchema):
    """Payload to create a generic library item."""

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "item_type": "SKILL",
                    "title": "FastAPI dependency override",
                    "summary": "Override narrow route dependencies in tests.",
                    "content": "Use app.dependency_overrides with a fake service.",
                    "category_id": "00000000-0000-4000-8000-000000000002",
                    "tags": ["fastapi", "testing"],
                    "status": "DRAFT",
                    "source_type": "USER_CREATED",
                    "created_by_type": "USER",
                    "created_by_name": "alex",
                    "details": {"risk_level": "LOW"},
                }
            ]
        }
    )

    item_type: ItemType
    title: str = Field(min_length=1)
    summary: str | None = None
    content: str = Field(min_length=1)
    category_id: str | None = None
    tags: list[str] = Field(default_factory=list)
    status: ItemStatus = ItemStatus.DRAFT
    source_type: SourceType = SourceType.USER_CREATED
    created_by_type: CreatedByType
    created_by_name: str
    details: dict[str, JSONValue] = Field(default_factory=dict)

    @field_validator("item_type", mode="before")
    @classmethod
    # Broad type justified: Pydantic before validators receive raw boundary input before contract validation.
    def parse_item_type(cls, value: object) -> ItemType:
        """Parse JSON item type values.

        Args:
            value [object]: Value supplied to parse_item_type.

        Returns:
            ItemType: Value produced by parse_item_type.
        """
        return _item_type(value)

    @field_validator("status", mode="before")
    @classmethod
    # Broad type justified: Pydantic before validators receive raw boundary input before contract validation.
    def parse_status(cls, value: object) -> ItemStatus:
        """Parse JSON status values.

        Args:
            value [object]: Value supplied to parse_status.

        Returns:
            ItemStatus: Value produced by parse_status.
        """
        return _item_status(value)

    @field_validator("source_type", mode="before")
    @classmethod
    # Broad type justified: Pydantic before validators receive raw boundary input before contract validation.
    def parse_source_type(cls, value: object) -> SourceType:
        """Parse JSON source type values.

        Args:
            value [object]: Value supplied to parse_source_type.

        Returns:
            SourceType: Value produced by parse_source_type.
        """
        return _source_type(value)

    @field_validator("created_by_type", mode="before")
    @classmethod
    # Broad type justified: Pydantic before validators receive raw boundary input before contract validation.
    def parse_created_by_type(cls, value: object) -> CreatedByType:
        """Parse JSON creator type values.

        Args:
            value [object]: Value supplied to parse_created_by_type.

        Returns:
            CreatedByType: Value produced by parse_created_by_type.
        """
        return _created_by_type(value)


class ItemUpdateRequest(StrictSchema):
    """Patch payload for generic item metadata or details."""

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "title": "FastAPI dependency overrides",
                    "tags": ["fastapi", "tests"],
                    "status": "ACTIVE",
                    "details": {"version": "1.0.1"},
                }
            ]
        }
    )

    title: str | None = None
    summary: str | None = None
    content: str | None = None
    category_id: str | None = None
    tags: list[str] | None = None
    status: ItemStatus | None = None
    details: dict[str, JSONValue] | None = None

    @field_validator("status", mode="before")
    @classmethod
    # Broad type justified: Pydantic before validators receive raw boundary input before contract validation.
    def parse_status(cls, value: object) -> ItemStatus | None:
        """Parse JSON status values when provided.

        Args:
            value [object]: Value supplied to parse_status.

        Returns:
            ItemStatus | None: Value produced by parse_status.
        """
        if value is None:
            return None
        return _item_status(value)


class ItemResponse(StrictSchema):
    """Canonical response schema for all library items."""

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "id": "00000000-0000-4000-8000-000000000010",
                    "item_type": "SKILL",
                    "title": "FastAPI dependency override",
                    "summary": "Override narrow route dependencies in tests.",
                    "content": "Use app.dependency_overrides with a fake service.",
                    "category_id": "00000000-0000-4000-8000-000000000002",
                    "tags": ["fastapi", "testing"],
                    "status": "ACTIVE",
                    "source_type": "USER_CREATED",
                    "created_by_type": "USER",
                    "created_by_name": "alex",
                    "details": {"risk_level": "LOW"},
                    "created_at": "2026-05-12T10:00:00Z",
                    "updated_at": "2026-05-12T10:05:00Z",
                }
            ]
        }
    )

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
    details: dict[str, JSONValue]
    created_at: datetime
    updated_at: datetime

    @field_validator("item_type", mode="before")
    @classmethod
    # Broad type justified: Pydantic before validators receive raw boundary input before contract validation.
    def parse_item_type(cls, value: object) -> ItemType:
        """Parse response item type values from repository payloads.

        Args:
            value [object]: Value supplied to parse_item_type.

        Returns:
            ItemType: Value produced by parse_item_type.
        """
        return _item_type(value)

    @field_validator("status", mode="before")
    @classmethod
    # Broad type justified: Pydantic before validators receive raw boundary input before contract validation.
    def parse_status(cls, value: object) -> ItemStatus:
        """Parse response status values from repository payloads.

        Args:
            value [object]: Value supplied to parse_status.

        Returns:
            ItemStatus: Value produced by parse_status.
        """
        return _item_status(value)

    @field_validator("source_type", mode="before")
    @classmethod
    # Broad type justified: Pydantic before validators receive raw boundary input before contract validation.
    def parse_source_type(cls, value: object) -> SourceType:
        """Parse response source type values from repository payloads.

        Args:
            value [object]: Value supplied to parse_source_type.

        Returns:
            SourceType: Value produced by parse_source_type.
        """
        return _source_type(value)

    @field_validator("created_by_type", mode="before")
    @classmethod
    # Broad type justified: Pydantic before validators receive raw boundary input before contract validation.
    def parse_created_by_type(cls, value: object) -> CreatedByType:
        """Parse response creator type values from repository payloads.

        Args:
            value [object]: Value supplied to parse_created_by_type.

        Returns:
            CreatedByType: Value produced by parse_created_by_type.
        """
        return _created_by_type(value)

    def to_public(self) -> dict[str, JSONValue]:
        """Serialize with JSON friendly dict for FastAPI response.

        Returns:
            dict[str, JSONValue]: Value produced by to_public.
        """
        return self.model_dump(mode="json")


class ItemResponseList(StrictRootSchema[list[ItemResponse]]):
    """Root response schema for item response arrays."""


class ClassificationResponse(StrictSchema):
    """Classification result for text categorization."""

    model_config = ConfigDict(
        json_schema_extra={"examples": [{"label": "SKILL", "confidence": 0.83}]}
    )

    label: ItemType
    confidence: float = Field(ge=0.0, le=1.0)

    @field_validator("label", mode="before")
    @classmethod
    # Broad type justified: Pydantic before validators receive raw boundary input before contract validation.
    def parse_label(cls, value: object) -> ItemType:
        """Parse response classification labels from raw string payloads.

        Args:
            value [object]: Value supplied to parse_label.

        Returns:
            ItemType: Value produced by parse_label.
        """
        return _item_type(value)
