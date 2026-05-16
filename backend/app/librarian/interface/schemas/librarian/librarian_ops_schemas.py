"""Librarian operation request schemas."""

from __future__ import annotations

from app.library.domain.event_enum.item_enums import ItemType
from app.shared.schemas.common_schemas import StrictSchemaModel
from pydantic import ConfigDict, Field, field_validator


class RecommendRequest(StrictSchemaModel):
    """Input to recommendation endpoint."""

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [{"query": "fastapi testing", "item_type": "SKILL", "limit": 5}]
        }
    )

    query: str = Field(min_length=1)
    item_type: ItemType = Field(default=ItemType.SKILL)
    limit: int = Field(default=5, ge=1, le=20)

    @field_validator("item_type", mode="before")
    @classmethod
    def parse_item_type(cls, value: str | ItemType) -> ItemType:
        """Accept public JSON item type values at the request boundary.

        Args:
            value [str | ItemType]: Value supplied to parse_item_type.

        Returns:
            ItemType: Value produced by parse_item_type.
        """
        if isinstance(value, ItemType):
            return value
        return ItemType(value)


class ClassifyRequest(StrictSchemaModel):
    """Input to classifier endpoint."""

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [{"text": "Create a workflow for reviewing generated skills."}]
        }
    )

    text: str = Field(min_length=1)


class CreateCandidateRequest(StrictSchemaModel):
    """Input to create skill candidate endpoint."""

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "provider_id": "00000000-0000-4000-8000-000000000456",
                    "prompt": "Create a skill for FastAPI dependency overrides.",
                    "category_id": "00000000-0000-4000-8000-000000000002",
                }
            ]
        }
    )

    provider_id: str
    prompt: str = Field(min_length=1)
    category_id: str | None = None
