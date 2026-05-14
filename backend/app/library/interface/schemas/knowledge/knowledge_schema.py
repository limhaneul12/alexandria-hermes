"""Knowledge request and response schemas."""

from __future__ import annotations

from app.library.domain.event_enum.item_enums import ItemStatus
from app.library.interface.schemas._types import StrictSchema
from app.shared.types.extra_types import JSONValue
from pydantic import ConfigDict, Field, field_validator


# Broad type justified: Pydantic before validators receive raw boundary input before contract validation.
def _item_status(value: object) -> ItemStatus:
    """Accept public JSON item status values at API boundaries."""
    if isinstance(value, ItemStatus):
        return value
    if isinstance(value, str):
        return ItemStatus(value)
    raise ValueError("status must be a valid item status")


class KnowledgeCreateRequest(StrictSchema):
    """Payload for adding reference-style knowledge."""

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "title": "Repository pattern notes",
                    "summary": "When to split repository ports.",
                    "content": "Routers should depend on narrow ports.",
                    "category_id": "00000000-0000-4000-8000-000000000002",
                    "tags": ["architecture"],
                    "body": "Use separate read and command ports when concerns diverge.",
                    "references": [
                        "backend/.agents/fastapi-dev-rule/07-di-and-wiring-rule.md"
                    ],
                    "related_items": ["00000000-0000-4000-8000-000000000010"],
                    "created_by_name": "alex",
                    "status": "DRAFT",
                }
            ]
        }
    )

    title: str = Field(min_length=1)
    summary: str | None = None
    content: str = Field(min_length=1)
    category_id: str | None = None
    tags: list[str] = Field(default_factory=list)
    body: str = Field(min_length=1)
    references: list[str] = Field(default_factory=list)
    related_items: list[str] = Field(default_factory=list)
    created_by_name: str
    status: ItemStatus = ItemStatus.DRAFT

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


class KnowledgePatchRequest(StrictSchema):
    """Patch payload for knowledge updates."""

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "summary": "Updated repository guidance.",
                    "tags": ["architecture", "repositories"],
                    "related_items": [
                        "00000000-0000-4000-8000-000000000010",
                        "00000000-0000-4000-8000-000000000012",
                    ],
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
    body: str | None = None
    references: list[str] | None = None
    related_items: list[str] | None = None

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


class KnowledgeResponse(StrictSchema):
    """Knowledge response payload."""

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "id": "00000000-0000-4000-8000-000000000011",
                    "item_type": "KNOWLEDGE",
                    "title": "Repository pattern notes",
                    "summary": "When to split repository ports.",
                    "content": "Routers should depend on narrow ports.",
                    "category_id": "00000000-0000-4000-8000-000000000002",
                    "tags": ["architecture"],
                    "details": {
                        "body": "Use separate read and command ports when concerns "
                        "diverge.",
                        "references": [
                            "backend/.agents/fastapi-dev-rule/07-di-and-wiring-rule.md"
                        ],
                        "related_items": ["00000000-0000-4000-8000-000000000010"],
                    },
                    "status": "ACTIVE",
                    "source_type": "USER_CREATED",
                    "created_by_type": "USER",
                    "created_by_name": "alex",
                }
            ]
        }
    )

    id: str
    item_type: str
    title: str
    summary: str | None
    content: str
    category_id: str | None
    tags: list[str]
    details: dict[str, JSONValue]
    status: str
    source_type: str
    created_by_type: str
    created_by_name: str
