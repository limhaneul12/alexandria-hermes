"""Service use cases for shared item management."""

from __future__ import annotations

from app.library.domain.contracts.item_contracts import ItemCreate, ItemUpdate
from app.library.domain.event_enum.item_enums import (
    CreatedByType,
    ItemStatus,
    ItemType,
    SourceType,
)
from app.library.domain.repositories.item_repository import IItemRepository
from app.library.domain.types.item_payload_types import (
    ItemUpdateValues,
    LibraryItemListResult,
    LibraryItemPayload,
    LibraryItemPayloadList,
)
from app.shared.exceptions import NotFoundError, ValidationError
from app.shared.types.extra_types import JSONObject, JSONValue
from app.shared.types.types_convert_utils import (
    enum_value,
    json_object_value,
    now_utc,
    required_string_value,
    string_items,
)


def _item_update_values(payload: dict[str, JSONValue]) -> ItemUpdateValues:
    """Convert raw patch payload into explicit item update fields.

    Args:
        payload: Patch payload from the API boundary.

    Returns:
        ItemUpdateValues: Typed patch fields accepted by the item repository.
    """
    values: ItemUpdateValues = {}
    if "title" in payload:
        values["title"] = required_string_value(payload["title"], "title")
    if "summary" in payload:
        summary = payload["summary"]
        values["summary"] = (
            None if summary is None else required_string_value(summary, "summary")
        )
    if "content" in payload:
        values["content"] = required_string_value(payload["content"], "content")
    if "category_id" in payload:
        category_id = payload["category_id"]
        values["category_id"] = (
            None
            if category_id is None
            else required_string_value(category_id, "category_id")
        )
    if "tags" in payload:
        values["tags"] = string_items(payload["tags"])
    if "status" in payload:
        values["status"] = enum_value(payload["status"], ItemStatus, "status")
    if "details" in payload:
        values["details"] = json_object_value(payload["details"])
    return values


class ItemService:
    """Item orchestration service."""

    def __init__(self, item_repo: IItemRepository) -> None:
        """Initialize item service dependencies."""
        self.item_repo = item_repo

    async def create_item(
        self,
        item_type: ItemType,
        title: str,
        summary: str | None,
        content: str,
        category_id: str | None,
        tags: list[str],
        status: ItemStatus,
        source_type: SourceType,
        created_by_type: CreatedByType,
        created_by_name: str,
        details: JSONObject,
    ) -> LibraryItemPayload:
        """Create one item and return API payload.

        Args:
            item_type: Item classification.
            title: Title text.
            summary: Optional summary.
            content: Main body.
            category_id: Optional category id.
            tags: Label tags.
            status: Publication status.
            source_type: Source path.
            created_by_type: Creator kind.
            created_by_name: Creator display name.
            details: Subtype specific detail payload.

        Returns:
            Item payload dictionary.
        """
        item_type = enum_value(item_type, ItemType, "item_type")
        status = enum_value(status, ItemStatus, "status")
        source_type = enum_value(source_type, SourceType, "source_type")
        created_by_type = enum_value(created_by_type, CreatedByType, "created_by_type")
        now = now_utc()
        model = await self.item_repo.create(
            payload=ItemCreate(
                item_type=item_type,
                title=title,
                summary=summary,
                content=content,
                category_id=category_id,
                tags=tags,
                status=status,
                source_type=source_type,
                created_by_type=created_by_type,
                created_by_name=created_by_name,
                created_at=now,
                updated_at=now,
                details=details,
                is_archived=status is ItemStatus.ARCHIVED,
            ),
        )
        return model.to_dict()

    async def update_item(
        self,
        item_id: str,
        payload: dict[str, JSONValue],
    ) -> LibraryItemPayload:
        """Patch item fields.

        Args:
            item_id: Target id.
            payload: Partial field map.

        Returns:
            Updated item payload.
        """
        if not payload:
            raise ValidationError("No fields to update")

        values = _item_update_values(payload)
        if not values:
            raise ValidationError("No fields to update")

        updated = await self.item_repo.update(
            item_id,
            payload=ItemUpdate(values=values),
        )
        return updated.to_dict()

    async def get_item(self, item_id: str) -> LibraryItemPayload:
        """Read one item by id.

        Args:
            item_id: Target id.

        Returns:
            Item payload dictionary.
        """
        model = await self.item_repo.get(item_id)
        if model is None:
            raise NotFoundError(f"Item not found: {item_id}")
        return model.to_dict()

    async def delete_item(self, item_id: str) -> None:
        """Delete one item.

        Args:
            item_id: Target id.

        Returns:
            None.
        """
        model = await self.item_repo.get(item_id)
        if model is None:
            raise NotFoundError(f"Item not found: {item_id}")
        await self.item_repo.delete(item_id)

    async def list_items(
        self,
        item_type: ItemType | None = None,
        limit: int = 100,
        offset: int = 0,
        category_id: str | None = None,
        search_query: str | None = None,
    ) -> LibraryItemListResult:
        """List all items with optional filters.

        Args:
            item_type: Optional item type.
            limit: Page size.
            offset: Offset.
            category_id: Optional category filter.
            search_query: Optional text filter.

        Returns:
            Tuple of ``(items, total_count)``.
        """
        if item_type is not None:
            item_type = enum_value(item_type, ItemType, "item_type")
        if item_type is None:
            rows, count = await self.item_repo.list_all(
                limit=limit,
                offset=offset,
                category_id=category_id,
                search_query=search_query,
            )
        else:
            rows = await self.item_repo.list_by_type(
                item_type=item_type,
                limit=limit,
                offset=offset,
            )
            if category_id is not None:
                rows = [row for row in rows if row.category_id == category_id]
            if search_query:
                pattern = search_query.strip().lower()
                rows = [
                    row
                    for row in rows
                    if pattern in row.title.lower()
                    or pattern in ("" if row.summary is None else row.summary).lower()
                    or pattern in row.content.lower()
                ]
            count = len(rows)
        return [row.to_dict() for row in rows], count

    async def search(
        self,
        query: str,
        item_type: ItemType | None = None,
    ) -> LibraryItemPayloadList:
        """Search across all items via FTS5.

        Args:
            query: Search input.
            item_type: Optional filter.

        Returns:
            Matched item payload list.
        """
        if not query.strip():
            return []
        if item_type is not None:
            item_type = enum_value(item_type, ItemType, "item_type")
        rows = await self.item_repo.search(
            query=query,
            item_type=item_type,
        )
        return [row.to_dict() for row in rows]
