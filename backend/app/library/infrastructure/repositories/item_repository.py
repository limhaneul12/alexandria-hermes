"""SQLAlchemy implementation of library item repository operations."""

from __future__ import annotations

import re
from datetime import UTC, datetime

from app.library.domain.entities.enums import ItemType
from app.library.domain.entities.read_models import LibraryItem
from app.library.domain.repositories.item_repository import ItemRepository
from app.library.infrastructure.models.item import LibraryItemORM
from app.shared.exceptions import NotFoundError
from app.shared.types.extra_types import JSONValue
from sqlalchemy import delete, func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

FTS_TOKEN_PATTERN = re.compile(r"\w+")


def _details_from(row: LibraryItemORM) -> dict[str, JSONValue]:
    """Return a typed details dictionary from an ORM row."""
    details = row.details
    return details if isinstance(details, dict) else {}


def _tags_from(row: LibraryItemORM) -> list[str]:
    """Return a typed tags list from an ORM row."""
    tags = row.tags
    return tags if isinstance(tags, list) else []


def _to_read_model(row: LibraryItemORM) -> LibraryItem:
    """Map an item ORM row into the domain read model."""
    return LibraryItem(
        id=row.id,
        item_type=row.item_type,
        title=row.title,
        summary=row.summary,
        content=row.content,
        category_id=row.category_id,
        tags=_tags_from(row),
        status=row.status,
        source_type=row.source_type,
        created_by_type=row.created_by_type,
        created_by_name=row.created_by_name,
        details=_details_from(row),
        created_at=row.created_at,
        updated_at=row.updated_at,
        is_archived=row.is_archived,
    )


class SqlAlchemyItemRepository(ItemRepository):
    """Concrete repository for library item persistence."""

    def __init__(self, *, session: AsyncSession) -> None:
        """Initialize repository.

        Args:
            session: Active async session.
        """
        self._session = session

    async def create(self, *, payload: dict[str, JSONValue]) -> LibraryItem:
        """Persist one library item.

        Args:
            payload: Dictionary used to initialize ORM object.

        Return:
            Created ORM object.
        """
        model = LibraryItemORM(**payload)
        self._session.add(model)
        await self._session.flush()
        await self.upsert_fts(model)
        return _to_read_model(model)

    async def update(
        self,
        item_id: str,
        *,
        payload: dict[str, JSONValue],
    ) -> LibraryItem:
        """Patch fields and refresh the updated timestamp.

        Args:
            item_id: Target record identifier.
            payload: Field map to apply.

        Return:
            Updated ORM object.
        """
        model = await self._session.get(LibraryItemORM, item_id)
        if model is None:
            raise NotFoundError(f"Item not found: {item_id}")

        for key, value in payload.items():
            setattr(model, key, value)
        model.updated_at = datetime.now(UTC)
        await self._session.flush()
        await self.upsert_fts(model)
        return _to_read_model(model)

    async def get(self, item_id: str) -> LibraryItem | None:
        """Get one item by primary key.

        Args:
            item_id: Target record identifier.

        Return:
            Item ORM object or ``None``.
        """
        model = await self._session.get(LibraryItemORM, item_id)
        return None if model is None else _to_read_model(model)

    async def delete(self, item_id: str) -> None:
        """Delete one item and remove FTS rows.

        Args:
            item_id: Target record identifier.

        Return:
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

        Return:
            Matching ORM rows.
        """
        statement = select(LibraryItemORM).where(
            LibraryItemORM.item_type == item_type.value
        )
        if limit is not None:
            statement = statement.limit(limit).offset(offset)
        rows = await self._session.execute(statement)
        return [_to_read_model(row) for row in rows.scalars().all()]

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

        Return:
            Tuple of (items, total_count).
        """
        statement = select(LibraryItemORM)
        if category_id is not None:
            statement = statement.where(LibraryItemORM.category_id == category_id)
        if search_query:
            pattern = f"%{search_query.strip().lower()}%"
            statement = statement.where(
                func.lower(LibraryItemORM.title).like(pattern)
                | func.lower(LibraryItemORM.summary).like(pattern)
                | func.lower(LibraryItemORM.content).like(pattern),
            )

        count = await self._session.scalar(
            select(func.count()).select_from(statement.subquery()),
        )
        total = 0 if count is None else int(count)

        statement = statement.order_by(LibraryItemORM.updated_at.desc())
        if limit is not None:
            statement = statement.limit(limit).offset(offset)

        rows = await self._session.execute(statement)
        return [_to_read_model(row) for row in rows.scalars().all()], total

    async def upsert_fts(self, item: LibraryItemORM) -> None:
        """Synchronize FTS index rows for one item.

        Args:
            item: Item ORM row.

        Return:
            None.
        """
        details = item.details
        if not isinstance(details, dict):
            details = {}

        tags = details.get("tags", item.tags)
        if isinstance(tags, list):
            tags_text = " ".join(str(tag) for tag in tags)
        else:
            tags_text = ""

        text_payload = " ".join(
            str(value)
            for value in [
                details.get("content", item.content),
                details.get("purpose", ""),
                details.get("summary", item.summary),
                details.get("body", ""),
                details.get("expected_result", ""),
            ]
            if value
        )

        await self._session.execute(
            text("DELETE FROM item_search_fts WHERE item_id = :item_id"),
            {"item_id": item.id},
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
            {
                "item_id": item.id,
                "item_type": item.item_type,
                "title": item.title,
                "summary": "" if item.summary is None else item.summary,
                "content": text_payload,
                "tags": tags_text,
                "details": str(details),
            },
        )

    async def remove_fts(self, item_id: str) -> None:
        """Remove stale search index rows.

        Args:
            item_id: Target item identifier.

        Return:
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

        Return:
            Matched ORM rows.
        """
        tokens = FTS_TOKEN_PATTERN.findall(query.strip())
        if not tokens:
            return []
        normalized = " ".join(f"{token}*" for token in tokens)
        fts_query = (
            "SELECT item_id FROM item_search_fts WHERE item_search_fts MATCH :query"
        )
        if item_type is not None:
            fts_query += " AND item_type = :item_type"

        ids_result = await self._session.execute(
            text(fts_query),
            {
                "query": normalized,
                "item_type": item_type.value if item_type is not None else None,
            },
        )
        ids = [row[0] for row in ids_result.all()]
        if not ids:
            return []

        rows = await self._session.execute(
            select(LibraryItemORM).where(LibraryItemORM.id.in_(ids))
        )
        return [_to_read_model(row) for row in rows.scalars().all()]
