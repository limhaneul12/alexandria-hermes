"""Item repository abstraction."""

from __future__ import annotations

from abc import ABC, abstractmethod

from app.library.domain.contracts.item_contracts import ItemCreate, ItemUpdate
from app.library.domain.entities.item_search_hit import ItemSearchCandidate
from app.library.domain.entities.item_search_query import ItemSearchQuery
from app.library.domain.entities.read_models import LibraryItem
from app.library.domain.event_enum.item_enums import ItemType


class IItemRepository(ABC):
    """Persistence contract for library item operations."""

    @abstractmethod
    async def create(self, *, payload: ItemCreate) -> LibraryItem:
        """Create a new item from persisted payload.

        Args:
            payload: Dictionary of ORM fields.

        Returns:
            Persisted ORM object.
        """

    @abstractmethod
    async def update(
        self,
        item_id: str,
        *,
        payload: ItemUpdate,
    ) -> LibraryItem:
        """Apply partial update to an existing item.

        Args:
            item_id: Target identifier.
            payload: Partial field map.

        Returns:
            Updated ORM object.
        """

    @abstractmethod
    async def get(self, item_id: str) -> LibraryItem | None:
        """Get one item by identifier.

        Args:
            item_id: Target identifier.

        Returns:
            ORM item or ``None``.
        """

    @abstractmethod
    async def delete(self, item_id: str) -> None:
        """Delete item row and related references.

        Args:
            item_id: Target identifier.

        Returns:
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

        Returns:
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

        Returns:
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

        Returns:
            Matching ORM rows.
        """

    @abstractmethod
    async def search_candidates(
        self,
        options: ItemSearchQuery,
    ) -> tuple[list[ItemSearchCandidate], int]:
        """Search items and return candidate projections without full content.

        Args:
            options: Normalized candidate search options.

        Returns:
            Tuple of matching candidate rows and total count before pagination.
        """
