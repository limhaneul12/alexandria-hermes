"""Knowledge service use cases."""

from __future__ import annotations

from collections.abc import Mapping

from app.library.application.item_service import ItemService
from app.library.domain.event_enum.item_enums import (
    CreatedByType,
    ItemStatus,
    ItemType,
    LibraryItemPatchField,
    SourceType,
)
from app.library.domain.event_enum.knowledge_enums import KnowledgeDetailField
from app.library.domain.types.item_payload_types import (
    LibraryItemListResult,
    LibraryItemPayload,
)
from app.shared.exceptions import ValidationError
from app.shared.types.extra_types import JSONValue


class KnowledgeService:
    """Service for knowledge library entries."""

    def __init__(self, item_service: ItemService) -> None:
        """Initialize service.

        Args:
            item_service: Shared item service.
        """
        self.item_service = item_service

    async def create_knowledge(
        self,
        title: str,
        summary: str | None,
        content: str,
        category_id: str | None,
        tags: list[str],
        body: str,
        references: list[str],
        related_items: list[str],
        created_by_name: str,
        activate: bool = True,
        status: ItemStatus | None = None,
    ) -> LibraryItemPayload:
        """Create knowledge entry.

        Args:
            title: Knowledge title.
            summary: Optional summary.
            content: Raw text content.
            category_id: Optional category.
            tags: Tags.
            body: Knowledge body detail.
            references: Reference links.
            related_items: Related item IDs.
            created_by_name: Actor name.
            activate: Whether to mark active.
            status: Optional forced status.

        Returns:
            Item payload.
        """
        resolved_status = (
            (ItemStatus.ACTIVE if activate else ItemStatus.DRAFT)
            if status is None
            else status
        )
        return await self.item_service.create_item(
            item_type=ItemType.KNOWLEDGE,
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
                "body": body,
                "references": references,
                "related_items": related_items,
            },
        )

    async def list_knowledge(
        self,
        limit: int = 100,
        offset: int = 0,
    ) -> LibraryItemListResult:
        """List knowledge items.

        Args:
            limit: Page size.
            offset: Page offset.

        Returns:
            Tuple of payload list and total.
        """
        return await self.item_service.list_items(
            item_type=ItemType.KNOWLEDGE,
            limit=limit,
            offset=offset,
        )

    async def patch_knowledge(
        self,
        item_id: str,
        payload: Mapping[str, JSONValue],
    ) -> LibraryItemPayload:
        """Patch one knowledge entry.

        Args:
            item_id: Target ID.
            payload: Patch payload map.

        Returns:
            Patched payload.
        """
        item = await self.item_service.get_item(item_id)
        if item["item_type"] != ItemType.KNOWLEDGE:
            raise ValidationError("Not a knowledge item")

        base_fields = {
            key: value
            for key, value in payload.items()
            if any(key == field.value for field in LibraryItemPatchField)
        }

        detail_updates: dict[str, JSONValue] = {}
        for field in KnowledgeDetailField:
            key = field.value
            if key in payload:
                detail_updates[key] = payload[key]

        if detail_updates:
            details = item["details"].copy()
            details.update(detail_updates)
            base_fields["details"] = details

        if not base_fields:
            raise ValidationError("No fields provided")

        return await self.item_service.update_item(item_id, payload=base_fields)
