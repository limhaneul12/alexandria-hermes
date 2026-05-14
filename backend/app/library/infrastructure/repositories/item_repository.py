"""SQLAlchemy implementation of library item repository operations."""

from __future__ import annotations

from datetime import UTC, datetime

from app.library.domain.contracts.item_contracts import ItemCreate, ItemUpdate
from app.library.domain.entities.read_models import LibraryItem
from app.library.domain.event_enum.item_enums import ItemType
from app.library.domain.repositories.item_repository import IItemRepository
from app.library.infrastructure.models.item_models import LibraryItemORM
from app.library.infrastructure.repositories.items.fts import (
    build_item_fts_payload,
    build_item_fts_query,
)
from app.library.infrastructure.repositories.items.mapping import (
    map_item_row_to_read_model,
)
from app.library.infrastructure.repositories.items.queries import (
    build_items_by_type_statement,
    build_items_count_statement,
    build_items_filtered_statement,
    build_items_page_statement,
)
from app.shared.exceptions import NotFoundError
from sqlalchemy import delete, select, text
from sqlalchemy.ext.asyncio import AsyncSession


class SqlAlchemyItemRepository(IItemRepository):
    """Concrete repository for library item persistence."""

    def __init__(self, *, session: AsyncSession) -> None:
        """Initialize repository.

        Args:
            session: Active async session.
        """
        self._session = session

    async def create(self, *, payload: ItemCreate) -> LibraryItem:
        """Persist one library item.

        Args:
            payload: Dictionary used to initialize ORM object.

        Returns:
            Created ORM object.
        """
        model = LibraryItemORM(**payload.to_record())
        self._session.add(model)
        await self._session.flush()
        await self.upsert_fts(model)
        return map_item_row_to_read_model(model)

    async def update(
        self,
        item_id: str,
        *,
        payload: ItemUpdate,
    ) -> LibraryItem:
        """Patch fields and refresh the updated timestamp.

        Args:
            item_id: Target record identifier.
            payload: Field map to apply.

        Returns:
            Updated ORM object.
        """
        model = await self._session.get(LibraryItemORM, item_id)
        if model is None:
            raise NotFoundError(f"Item not found: {item_id}")

        values = payload.to_record()
        if "title" in values:
            model.title = values["title"]
        if "summary" in values:
            model.summary = values["summary"]
        if "content" in values:
            model.content = values["content"]
        if "category_id" in values:
            model.category_id = values["category_id"]
        if "tags" in values:
            model.tags = values["tags"]
        if "status" in values:
            model.status = values["status"].value
        if "details" in values:
            model.details = values["details"]
        model.updated_at = datetime.now(UTC)
        await self._session.flush()
        await self.upsert_fts(model)
        return map_item_row_to_read_model(model)

    async def get(self, item_id: str) -> LibraryItem | None:
        """Get one item by primary key.

        Args:
            item_id: Target record identifier.

        Returns:
            Item ORM object or ``None``.
        """
        model = await self._session.get(LibraryItemORM, item_id)
        return None if model is None else map_item_row_to_read_model(model)

    async def delete(self, item_id: str) -> None:
        """Delete one item and remove FTS rows.

        Args:
            item_id: Target record identifier.

        Returns:
            None.
        """
        model = await self._session.get(LibraryItemORM, item_id)
        if model is None:
            raise NotFoundError(f"Item not found: {item_id}")

        await self.remove_fts(item_id)
        await self._session.execute(
            delete(LibraryItemORM).where(LibraryItemORM.id == item_id),
        )
        await self._session.flush()

    async def list_by_type(
        self,
        *,
        item_type: ItemType,
        limit: int | None = None,
        offset: int = 0,
    ) -> list[LibraryItem]:
        """List items filtered by item type.

        Args:
            item_type: Domain type filter.
            limit: Optional item limit.
            offset: Optional offset.

        Returns:
            Matching ORM rows.
        """
        statement = build_items_by_type_statement(
            item_type=item_type,
            limit=limit,
            offset=offset,
        )
        rows = await self._session.execute(statement)
        return [map_item_row_to_read_model(row) for row in rows.scalars().all()]

    async def list_all(
        self,
        *,
        limit: int | None = None,
        offset: int = 0,
        category_id: str | None = None,
        search_query: str | None = None,
    ) -> tuple[list[LibraryItem], int]:
        """List all items with optional filters.

        Args:
            limit: Optional item limit.
            offset: Optional offset.
            category_id: Optional category filter.
            search_query: Optional title/summary/content like search.

        Returns:
            Tuple of (items, total_count).
        """
        statement = build_items_filtered_statement(
            category_id=category_id,
            search_query=search_query,
        )
        count = await self._session.scalar(build_items_count_statement(statement))
        total = 0 if count is None else int(count)

        page_statement = build_items_page_statement(
            statement,
            limit=limit,
            offset=offset,
        )
        rows = await self._session.execute(page_statement)
        return [map_item_row_to_read_model(row) for row in rows.scalars().all()], total

    async def upsert_fts(self, item: LibraryItemORM) -> None:
        """Synchronize FTS index rows for one item.

        Args:
            item: Item ORM row.

        Returns:
            None.
        """
        fts_payload = build_item_fts_payload(item)
        await self._session.execute(
            text("DELETE FROM item_search_fts WHERE item_id = :item_id"),
            {"item_id": fts_payload.item_id},
        )
        await self._session.execute(
            text(
                """
                INSERT INTO item_search_fts(
                    item_id,
                    item_type,
                    title,
                    summary,
                    content,
                    tags,
                    details
                )
                VALUES (:item_id, :item_type, :title, :summary, :content, :tags, :details)
                """
            ),
            fts_payload.as_parameters(),
        )

    async def remove_fts(self, item_id: str) -> None:
        """Remove stale search index rows.

        Args:
            item_id: Target item identifier.

        Returns:
            None.
        """
        await self._session.execute(
            text("DELETE FROM item_search_fts WHERE item_id = :item_id"),
            {"item_id": item_id},
        )

    async def search(
        self, query: str, item_type: ItemType | None = None
    ) -> list[LibraryItem]:
        """Run FTS query against text index and return ORM rows.

        Args:
            query: Raw user search text.
            item_type: Optional type filter.

        Returns:
            Matched ORM rows.
        """
        fts_query = build_item_fts_query(query, item_type)
        if fts_query is None:
            return []

        ids_result = await self._session.execute(
            text(fts_query.sql),
            fts_query.parameters,
        )
        ids = [row[0] for row in ids_result.all()]
        if not ids:
            return []

        rows = await self._session.execute(
            select(LibraryItemORM).where(LibraryItemORM.id.in_(ids))
        )
        return [map_item_row_to_read_model(row) for row in rows.scalars().all()]
