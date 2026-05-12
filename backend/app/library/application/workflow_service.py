"""Workflow service use cases."""

from __future__ import annotations

from collections.abc import Mapping

from app.library.application.item_service import ItemService
from app.library.domain.entities.enums import (
    CreatedByType,
    ItemStatus,
    ItemType,
    SourceType,
)
from app.shared.exceptions import ValidationError
from app.shared.types.extra_types import JSONValue


class WorkflowService:
    """Service for workflow registrations and updates."""

    def __init__(self, item_service: ItemService) -> None:
        """Initialize service.

        Args:
            item_service: Shared item service.
        """
        self.item_service = item_service

    async def create_workflow(
        self,
        *,
        title: str,
        summary: str | None,
        content: str,
        category_id: int | None,
        tags: list[str],
        steps: list[str],
        related_skill_ids: list[int],
        expected_result: str | None,
        use_case: str | None,
        created_by_name: str,
        activate: bool = True,
        status: ItemStatus | None = None,
    ) -> dict[str, JSONValue]:
        """Create a workflow entry.

        Args:
            title: Workflow title.
            summary: Optional summary.
            content: Workflow body.
            category_id: Optional category.
            tags: Tag list.
            steps: Ordered step list.
            related_skill_ids: Referenced skill IDs.
            expected_result: Expected end state.
            use_case: Usage example.
            created_by_name: Actor name.
            activate: Default activation flag.
            status: Optional forced status.

        Return:
            Item payload.
        """
        resolved_status = (
            (ItemStatus.ACTIVE if activate else ItemStatus.DRAFT)
            if status is None
            else status
        )
        return await self.item_service.create_item(
            item_type=ItemType.WORKFLOW,
            title=title,
            summary=summary,
            content=content,
            category_id=category_id,
            tags=tags,
            status=resolved_status,
            source_type=SourceType.USER_CREATED,
            created_by_type=CreatedByType.USER,
            created_by_name=created_by_name,
            details={
                "steps": steps,
                "related_skill_ids": related_skill_ids,
                "expected_result": expected_result,
                "use_case": use_case,
            },
        )

    async def list_workflows(
        self,
        *,
        limit: int = 100,
        offset: int = 0,
    ) -> tuple[list[dict[str, JSONValue]], int]:
        """List workflow items.

        Args:
            limit: Page size.
            offset: Page offset.

        Return:
            Tuple of payload list and total.
        """
        return await self.item_service.list_items(
            item_type=ItemType.WORKFLOW,
            limit=limit,
            offset=offset,
        )

    async def patch_workflow(
        self,
        *,
        item_id: int,
        payload: Mapping[str, JSONValue],
    ) -> dict[str, JSONValue]:
        """Patch one workflow entry.

        Args:
            item_id: Target ID.
            payload: Patch payload map.

        Return:
            Patched payload.
        """
        item = await self.item_service.get_item(item_id)
        if item["item_type"] != ItemType.WORKFLOW:
            raise ValidationError("Not a workflow item")

        base_fields = {
            key: value
            for key, value in payload.items()
            if key in {"title", "summary", "content", "category_id", "tags", "status"}
        }

        detail_fields: dict[str, JSONValue] = {}
        for key in ["steps", "related_skill_ids", "expected_result", "use_case"]:
            if key in payload:
                detail_fields[key] = payload[key]

        if detail_fields:
            detail_payload = item.get("details")
            if isinstance(detail_payload, dict):
                details = detail_payload.copy()
            else:
                details = {}
            details.update(detail_fields)
            base_fields["details"] = details

        if not base_fields:
            raise ValidationError("No fields provided")

        return await self.item_service.update_item(item_id, payload=base_fields)
