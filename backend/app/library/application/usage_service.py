"""Usage tracking and analytics service."""

from __future__ import annotations

from app.library.domain.contracts.usage_contracts import UsageCreate
from app.library.domain.entities.read_models import UsageHistory
from app.library.domain.event_enum.usage_enums import SelectionSource
from app.library.domain.repositories.usage_repository import IUsageRepository
from app.library.domain.types.usage_payload_types import (
    PopularByCategoryPayload,
    PopularByCategoryPayloadList,
    PopularItemPayload,
    PopularItemPayloadList,
    UsageFeedbackPayload,
    UsageRecordCommandPayload,
    UsageRecordPayload,
    UsageRecordPayloadList,
)
from app.shared.types.types_convert_utils import enum_value


def _usage_feedback_payload(
    feedback: str | UsageFeedbackPayload | None,
) -> UsageFeedbackPayload | None:
    """Normalize public feedback input into a usage feedback object.

    Args:
        feedback: Optional feedback text or already-shaped feedback object.

    Returns:
        UsageFeedbackPayload | None: Feedback object for persistence.
    """
    if feedback is None:
        return None
    if isinstance(feedback, str):
        payload: UsageFeedbackPayload = {"comment": feedback}
        return payload
    return feedback.copy()


def _usage_record_payload(model: UsageHistory) -> UsageRecordPayload:
    """Return the public usage response payload for one read model.

    Args:
        model: Usage history read model.

    Returns:
        UsageRecordPayload: API-safe usage event payload.
    """
    payload: UsageRecordPayload = {
        "id": model.id,
        "item_id": model.item_id,
        "item_type": model.item_type,
        "agent_name": model.agent_name,
        "librarian_provider": model.librarian_provider,
        "selection_source": enum_value(
            model.selection_source, SelectionSource, "selection_source"
        ),
        "used_at": model.used_at,
        "success": model.success,
    }
    return payload


class UsageService:
    """Service wrapper for usage history operations."""

    def __init__(self, usage_repo: IUsageRepository) -> None:
        """Initialize usage service dependencies."""
        self.usage_repo = usage_repo

    async def record_usage(
        self, payload: UsageRecordCommandPayload
    ) -> UsageRecordPayload:
        """Persist a usage event and return its response payload.

        Args:
            payload: Validated interface payload containing usage event fields.

        Returns:
            UsageRecordPayload: Persisted usage event response payload.
        """
        model = await self.usage_repo.create(
            payload=UsageCreate(
                item_id=payload["item_id"],
                item_type=payload["item_type"],
                agent_name=payload["agent_name"],
                librarian_provider=payload["librarian_provider"],
                query=payload["query"],
                selection_source=enum_value(
                    payload["selection_source"],
                    SelectionSource,
                    "selection_source",
                ),
                used_at=payload["used_at"],
                success=payload["success"],
                feedback=_usage_feedback_payload(payload["feedback"]),
            )
        )
        return _usage_record_payload(model)

    async def recent(self, limit: int = 20) -> UsageRecordPayloadList:
        """List recent usage events.

        Args:
            limit: Maximum number of recent usage events to return.

        Returns:
            UsageRecordPayloadList: Recent usage event payloads.
        """
        rows = await self.usage_repo.recent(limit=limit)
        return [_usage_record_payload(row) for row in rows]

    async def popular(self, limit: int = 10) -> PopularItemPayloadList:
        """List the most-used items by usage count.

        Args:
            limit: Maximum number of item-count rows to return.

        Returns:
            PopularItemPayloadList: Popular item id/count payloads.
        """
        data = await self.usage_repo.popular(limit=limit)
        return [_popular_item_payload(item_id, count) for item_id, count in data]

    async def popular_by_category(
        self, limit: int = 10
    ) -> PopularByCategoryPayloadList:
        """List usage counts grouped by category and item type.

        Args:
            limit: Maximum number of category-count rows to return.

        Returns:
            PopularByCategoryPayloadList: Category usage summary payloads.
        """
        data = await self.usage_repo.popular_by_category(limit=limit)
        return [
            _popular_by_category_payload(category_id, item_type, count)
            for category_id, item_type, count in data
        ]

    async def by_item(self, item_id: str) -> UsageRecordPayloadList:
        """List usage history for one item.

        Args:
            item_id: Target library item identifier.

        Returns:
            UsageRecordPayloadList: Usage event payloads for the item.
        """
        rows = await self.usage_repo.list_by_item(item_id)
        return [_usage_record_payload(row) for row in rows]


def _popular_item_payload(item_id: str, count: int) -> PopularItemPayload:
    """Return the public popular-item payload for one aggregate row.

    Args:
        item_id: Library item identifier.
        count: Usage count.

    Returns:
        PopularItemPayload: API-safe popular item payload.
    """
    payload: PopularItemPayload = {"item_id": item_id, "count": count}
    return payload


def _popular_by_category_payload(
    category_id: str, item_type: str, count: int
) -> PopularByCategoryPayload:
    """Return the public popular-category payload for one aggregate row.

    Args:
        category_id: Library category identifier.
        item_type: Library item type string.
        count: Usage count.

    Returns:
        PopularByCategoryPayload: API-safe category aggregate payload.
    """
    payload: PopularByCategoryPayload = {
        "category_id": category_id,
        "item_type": item_type,
        "count": count,
    }
    return payload
