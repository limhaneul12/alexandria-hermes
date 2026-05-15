"""Search request/response schemas."""

from __future__ import annotations

from app.library.domain.event_enum.item_enums import ItemType
from app.library.interface.schemas._types import StrictSchema
from pydantic import ConfigDict


class SearchQueryRequest(StrictSchema):
    """Shared search query model for item routes."""

    model_config = ConfigDict(
        json_schema_extra={"examples": [{"q": "fastapi testing", "limit": 10}]}
    )

    q: str
    limit: int | None = None


class SearchResponseItem(StrictSchema):
    """Search result payload for list responses."""

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "id": "00000000-0000-4000-8000-000000000010",
                    "item_type": "SKILL",
                    "title": "FastAPI dependency override",
                    "summary": "Override narrow route dependencies in tests.",
                    "category_id": "00000000-0000-4000-8000-000000000002",
                }
            ]
        }
    )

    id: str
    item_type: ItemType
    title: str
    summary: str | None
    category_id: str | None


class SearchResponse(StrictSchema):
    """Search response container."""

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "query": "fastapi testing",
                    "item_type": "SKILL",
                    "count": 1,
                    "items": [
                        {
                            "id": "00000000-0000-4000-8000-000000000010",
                            "item_type": "SKILL",
                            "title": "FastAPI dependency override",
                            "summary": "Override narrow route dependencies in tests.",
                            "category_id": "00000000-0000-4000-8000-000000000002",
                        }
                    ],
                }
            ]
        }
    )

    query: str
    item_type: str | None
    count: int
    items: list[SearchResponseItem]
