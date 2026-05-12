"""Shared schemas for generic item endpoints."""

from __future__ import annotations

from datetime import datetime

from app.library.domain.entities.enums import ItemStatus, ItemType, SourceType
from app.library.interface.schemas._types import StrictSchema
from app.shared.types.extra_types import JSONValue
from pydantic import ConfigDict, Field


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
                    "category_id": 2,
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
    category_id: int | None = None
    tags: list[str] = Field(default_factory=list)
    status: ItemStatus = ItemStatus.DRAFT
    source_type: SourceType = SourceType.USER_CREATED
    created_by_type: str
    created_by_name: str
    details: dict[str, JSONValue] = Field(default_factory=dict)


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
    category_id: int | None = None
    tags: list[str] | None = None
    status: ItemStatus | None = None
    details: dict[str, JSONValue] | None = None


class ItemResponse(StrictSchema):
    """Canonical response schema for all library items."""

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "id": 10,
                    "item_type": "SKILL",
                    "title": "FastAPI dependency override",
                    "summary": "Override narrow route dependencies in tests.",
                    "content": "Use app.dependency_overrides with a fake service.",
                    "category_id": 2,
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

    id: int
    item_type: ItemType
    title: str
    summary: str | None
    content: str
    category_id: int | None
    tags: list[str]
    status: ItemStatus
    source_type: SourceType
    created_by_type: str
    created_by_name: str
    details: dict[str, JSONValue]
    created_at: datetime
    updated_at: datetime

    def to_public(self) -> dict[str, JSONValue]:
        """Serialize with JSON friendly dict for FastAPI response."""
        return self.model_dump(mode="json")


class ClassificationResponse(StrictSchema):
    """Classification result for text categorization."""

    model_config = ConfigDict(
        json_schema_extra={"examples": [{"label": "SKILL", "confidence": 0.83}]}
    )

    label: ItemType
    confidence: float = Field(ge=0.0, le=1.0)
