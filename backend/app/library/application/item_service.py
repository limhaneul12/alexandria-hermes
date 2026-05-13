"""Service use cases for shared item management."""

from __future__ import annotations

from dataclasses import dataclass

from app.library.application.common import item_to_dict, now_utc
from app.library.domain.entities.enums import ItemStatus, ItemType, SourceType
from app.library.domain.repositories.item_repository import ItemRepository
from app.shared.exceptions import NotFoundError, ValidationError
from app.shared.types.extra_types import JSONValue


@dataclass(frozen=True)
class ItemService:
    """Item orchestration service."""

    item_repo: ItemRepository

    async def create_item(
        self,
        *,
        item_type: ItemType,
        title: str,
        summary: str | None,
        content: str,
        category_id: str | None,
        tags: list[str],
        status: ItemStatus,
        source_type: SourceType,
        created_by_type: str,
        created_by_name: str,
        details: dict[str, JSONValue],
    ) -> dict[str, JSONValue]:
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

        Return:
            Item payload dictionary.
        """
        now = now_utc()
        model = await self.item_repo.create(
            payload={
                "item_type": item_type.value,
                "title": title,
                "summary": summary,
                "content": content,
                "category_id": category_id,
                "tags": tags,
                "status": status.value,
                "source_type": source_type.value,
                "created_by_type": created_by_type,
                "created_by_name": created_by_name,
                "created_at": now,
                "updated_at": now,
                "details": details,
                "is_archived": status is ItemStatus.ARCHIVED,
            },
        )
        return item_to_dict(model)

    async def update_item(
        self,
        item_id: str,
        payload: dict[str, JSONValue],
    ) -> dict[str, JSONValue]:
        """Patch item fields.

        Args:
            item_id: Target id.
            payload: Partial field map.

        Return:
            Updated payload dictionary.
        """
        if not payload:
            raise ValidationError("No fields to update")

        updated = await self.item_repo.update(item_id, payload=payload)
        return item_to_dict(updated)

    async def get_item(self, item_id: str) -> dict[str, JSONValue]:
        """Read one item by id.

        Args:
            item_id: Target id.

        Return:
            Item payload dictionary.
        """
        model = await self.item_repo.get(item_id)
        if model is None:
            raise NotFoundError(f"Item not found: {item_id}")
        return item_to_dict(model)

    async def delete_item(self, item_id: str) -> None:
        """Delete one item.

        Args:
            item_id: Target id.

        Return:
            None.
        """
        model = await self.item_repo.get(item_id)
        if model is None:
            raise NotFoundError(f"Item not found: {item_id}")
        await self.item_repo.delete(item_id)

    async def list_items(
        self,
        *,
        item_type: ItemType | None = None,
        limit: int = 100,
        offset: int = 0,
        category_id: str | None = None,
        search_query: str | None = None,
    ) -> tuple[list[dict[str, JSONValue]], int]:
        """List all items with optional filters.

        Args:
            item_type: Optional item type.
            limit: Page size.
            offset: Offset.
            category_id: Optional category filter.
            search_query: Optional text filter.

        Return:
            Tuple of ``(items, total_count)``.
        """
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
        return [item_to_dict(row) for row in rows], count

    async def search(
        self,
        query: str,
        item_type: ItemType | None = None,
    ) -> list[dict[str, JSONValue]]:
        """Search across all items via FTS5.

        Args:
            query: Search input.
            item_type: Optional filter.

        Return:
            Matched item payload list.
        """
        if not query.strip():
            return []
        rows = await self.item_repo.search(
            query=query,
            item_type=item_type,
        )
        return [item_to_dict(row) for row in rows]
