"""Knowledge request and response schemas."""

from __future__ import annotations

from app.library.domain.entities.enums import ItemStatus
from app.library.interface.schemas._types import StrictSchema
from app.shared.types.extra_types import JSONValue
from pydantic import ConfigDict, Field


class KnowledgeCreateRequest(StrictSchema):
    """Payload for adding reference-style knowledge."""

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "title": "Repository pattern notes",
                    "summary": "When to split repository ports.",
                    "content": "Routers should depend on narrow ports.",
                    "category_id": 2,
                    "tags": ["architecture"],
                    "body": "Use separate read and command ports when concerns diverge.",
                    "references": [
                        "backend/.agents/fastapi-dev-rule/07-di-and-wiring-rule.md"
                    ],
                    "related_items": [10],
                    "created_by_name": "alex",
                    "status": "DRAFT",
                }
            ]
        }
    )

    title: str = Field(min_length=1)
    summary: str | None = None
    content: str = Field(min_length=1)
    category_id: int | None = None
    tags: list[str] = Field(default_factory=list)
    body: str = Field(min_length=1)
    references: list[str] = Field(default_factory=list)
    related_items: list[int] = Field(default_factory=list)
    created_by_name: str
    status: ItemStatus = ItemStatus.DRAFT


class KnowledgePatchRequest(StrictSchema):
    """Patch payload for knowledge updates."""

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "summary": "Updated repository guidance.",
                    "tags": ["architecture", "repositories"],
                    "related_items": [10, 12],
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
    body: str | None = None
    references: list[str] | None = None
    related_items: list[int] | None = None


class KnowledgeResponse(StrictSchema):
    """Knowledge response payload."""

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "id": 11,
                    "item_type": "KNOWLEDGE",
                    "title": "Repository pattern notes",
                    "summary": "When to split repository ports.",
                    "content": "Routers should depend on narrow ports.",
                    "category_id": 2,
                    "tags": ["architecture"],
                    "details": {
                        "body": "Use separate read and command ports when concerns "
                        "diverge.",
                        "references": [
                            "backend/.agents/fastapi-dev-rule/07-di-and-wiring-rule.md"
                        ],
                        "related_items": [10],
                    },
                    "status": "ACTIVE",
                    "source_type": "USER_CREATED",
                    "created_by_type": "USER",
                    "created_by_name": "alex",
                }
            ]
        }
    )

    id: int
    item_type: str
    title: str
    summary: str | None
    content: str
    category_id: int | None
    tags: list[str]
    details: dict[str, JSONValue]
    status: str
    source_type: str
    created_by_type: str
    created_by_name: str
