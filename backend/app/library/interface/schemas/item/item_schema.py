"""Shared schemas for generic item endpoints."""

from __future__ import annotations

from app.library.domain.event_enum.item_enums import (
    CreatedByType,
    ItemStatus,
    ItemType,
    SourceType,
)
from app.shared.schemas.common_schemas import StrictRootSchemaModel, StrictSchemaModel
from app.shared.schemas.datetime_schemas import AwareTimestamp
from app.shared.types.extra_types import JSONValue
from pydantic import ConfigDict, Field


class ItemCreateRequest(StrictSchemaModel):
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


class ItemUpdateRequest(StrictSchemaModel):
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


class ItemResponse(StrictSchemaModel):
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
    created_at: AwareTimestamp
    updated_at: AwareTimestamp

    def to_public(self) -> dict[str, JSONValue]:
        """Serialize with JSON friendly dict for FastAPI response.

        Returns:
            dict[str, JSONValue]: Value produced by to_public.
        """
        return self.model_dump(mode="json")


class ItemResponseList(StrictRootSchemaModel[list[ItemResponse]]):
    """Root response schema for item response arrays."""


class ClassificationResponse(StrictSchemaModel):
    """Classification result for text categorization."""

    model_config = ConfigDict(
        json_schema_extra={"examples": [{"label": "SKILL", "confidence": 0.83}]}
    )

    label: ItemType
    confidence: float = Field(ge=0.0, le=1.0)
