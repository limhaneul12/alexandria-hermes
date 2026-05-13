"""Item repository abstraction."""

from __future__ import annotations

from abc import ABC, abstractmethod

from app.library.domain.entities.enums import ItemType
from app.library.domain.entities.read_models import LibraryItem
from app.shared.types.extra_types import JSONValue


class ItemRepository(ABC):
    """Persistence contract for library item operations."""

    @abstractmethod
    async def create(self, *, payload: dict[str, JSONValue]) -> LibraryItem:
        """Create a new item from persisted payload.

        Args:
            payload: Dictionary of ORM fields.

        Return:
            Persisted ORM object.
        """

    @abstractmethod
    async def update(
        self,
        item_id: str,
        *,
        payload: dict[str, JSONValue],
    ) -> LibraryItem:
        """Apply partial update to an existing item.

        Args:
            item_id: Target identifier.
            payload: Partial field map.

        Return:
            Updated ORM object.
        """

    @abstractmethod
    async def get(self, item_id: str) -> LibraryItem | None:
        """Get one item by identifier.

        Args:
            item_id: Target identifier.

        Return:
            ORM item or ``None``.
        """

    @abstractmethod
    async def delete(self, item_id: str) -> None:
        """Delete item row and related references.

        Args:
            item_id: Target identifier.

        Return:
            None.
        """

    @abstractmethod
    async def list_by_type(
        self,
        *,
        item_type: ItemType,
        limit: int | None = None,
        offset: int = 0,
    ) -> list[LibraryItem]:
        """List items for one type.

        Args:
            item_type: Item category.
            limit: Optional limit.
            offset: Optional offset.

        Return:
            Matching items.
        """

    @abstractmethod
    async def list_all(
        self,
        *,
        limit: int | None = None,
        offset: int = 0,
        category_id: str | None = None,
        search_query: str | None = None,
    ) -> tuple[list[LibraryItem], int]:
        """List and count all items.

        Args:
            limit: Optional limit.
            offset: Optional offset.
            category_id: Optional category filter.
            search_query: Optional substring search text.

        Return:
            ``(items, total_count)``.
        """

    @abstractmethod
    async def search(
        self, query: str, item_type: ItemType | None = None
    ) -> list[LibraryItem]:
        """Search items using SQLite FTS5.

        Args:
            query: Search string.
            item_type: Optional type filter.

        Return:
            Matching ORM rows.
        """
