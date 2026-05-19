"""Usage tracking schemas."""

from __future__ import annotations

from datetime import datetime

from app.library.domain.event_enum.usage_enums import SelectionSource
from app.library.domain.types.usage_payload_types import (
    UsageFeedbackPayload,
    UsageRecordCommandPayload,
)
from app.shared.schemas.common_schemas import StrictRootSchemaModel, StrictSchemaModel
from app.shared.types.extra_types import JSONObject
from pydantic import ConfigDict


class UsageRecordRequest(StrictSchemaModel):
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
    feedback: str | JSONObject | None = None

    def to_payload(self, used_at: datetime) -> UsageRecordCommandPayload:
        """Return application command payload for recording usage.

        Args:
            used_at: Timestamp assigned by the HTTP boundary.

        Returns:
            UsageRecordCommandPayload: Typed command payload for UsageService.
        """
        payload: UsageRecordCommandPayload = {
            "item_id": self.item_id,
            "item_type": self.item_type,
            "agent_name": self.agent_name,
            "librarian_provider": self.librarian_provider,
            "query": self.query,
            "selection_source": self.selection_source,
            "used_at": used_at,
            "success": self.success,
            "feedback": _feedback_payload(self.feedback),
        }
        return payload


class UsageRecordResponse(StrictSchemaModel):
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


class UsageRecordResponseList(StrictRootSchemaModel[list[UsageRecordResponse]]):
    """Root response schema for usage record arrays."""


class PopularItemResponse(StrictSchemaModel):
    """Usage aggregate response."""

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {"item_id": "00000000-0000-4000-8000-000000000010", "count": 42}
            ]
        }
    )

    item_id: str
    count: int


class PopularItemResponseList(StrictRootSchemaModel[list[PopularItemResponse]]):
    """Root response schema for popular item arrays."""


class PopularByCategoryResponse(StrictSchemaModel):
    """Usage aggregate by category and type."""

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "category_id": "00000000-0000-4000-8000-000000000002",
                    "item_type": "SKILL",
                    "count": 12,
                }
            ]
        }
    )

    category_id: str
    item_type: str
    count: int


class PopularByCategoryResponseList(
    StrictRootSchemaModel[list[PopularByCategoryResponse]]
):
    """Root response schema for popular-by-category arrays."""


def _feedback_payload(
    value: str | JSONObject | None,
) -> str | UsageFeedbackPayload | None:
    """Normalize schema feedback into the application usage payload shape.

    Args:
        value: Optional string or JSON object feedback.

    Returns:
        Usage feedback payload accepted by the application service.
    """
    if value is None or isinstance(value, str):
        return value
    return UsageFeedbackPayload(**value)
