"""Usage tracking schemas."""

from __future__ import annotations

from datetime import datetime

from app.library.domain.entities.enums import SelectionSource
from app.library.interface.schemas._types import StrictSchema
from pydantic import ConfigDict, field_validator


class UsageRecordRequest(StrictSchema):
    """Payload for recording usage event."""

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "item_id": "00000000-0000-4000-8000-000000000010",
                    "item_type": "SKILL",
                    "agent_name": "research-agent",
                    "librarian_provider": "default-openai",
                    "query": "fastapi tests",
                    "selection_source": "SEARCH",
                    "success": True,
                    "feedback": "Useful result.",
                }
            ]
        }
    )

    item_id: str
    item_type: str
    agent_name: str
    librarian_provider: str | None = None
    query: str | None = None
    selection_source: SelectionSource
    success: bool
    feedback: str | None = None

    @field_validator("selection_source", mode="before")
    @classmethod
    def parse_selection_source(cls, value: object) -> SelectionSource:
        """Accept JSON enum values while preserving strict internal typing."""
        if isinstance(value, SelectionSource):
            return value
        if isinstance(value, str):
            return SelectionSource(value)
        raise ValueError("selection_source must be a valid selection source")


class UsageRecordResponse(StrictSchema):
    """Usage record response object."""

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "id": "00000000-0000-4000-8000-000000000099",
                    "item_id": "00000000-0000-4000-8000-000000000010",
                    "item_type": "SKILL",
                    "agent_name": "research-agent",
                    "librarian_provider": "default-openai",
                    "selection_source": "SEARCH",
                    "used_at": "2026-05-12T10:00:00Z",
                    "success": True,
                }
            ]
        }
    )

    id: str
    item_id: str
    item_type: str
    agent_name: str
    librarian_provider: str | None
    selection_source: SelectionSource
    used_at: datetime
    success: bool


class PopularItemResponse(StrictSchema):
    """Usage aggregate response."""

    model_config = ConfigDict(
        json_schema_extra={"examples": [{"item_id": "00000000-0000-4000-8000-000000000010", "count": 42}]}
    )

    item_id: str
    count: int


class PopularByCategoryResponse(StrictSchema):
    """Usage aggregate by category and type."""

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [{"category_id": "00000000-0000-4000-8000-000000000002", "item_type": "SKILL", "count": 12}]
        }
    )

    category_id: str
    item_type: str
    count: int
