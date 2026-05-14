"""Category repository abstraction."""

from __future__ import annotations

from abc import ABC, abstractmethod

from app.library.domain.entities.read_models import Category


class ICategoryRepository(ABC):
    """Persistence contract for category operations."""

    @abstractmethod
    async def list_all(self) -> list[Category]:
        """Return all categories ordered by display position.

        Returns:
            list[Category]: Value produced by list_all.
        """

    @abstractmethod
    async def create(self, *, name: str, parent_id: str | None = None) -> Category:
        """Create a new category node.

        Args:
            name [str]: Value supplied to create.
            parent_id [str | None]: Value supplied to create.

        Returns:
            Category: Value produced by create.
        """

    @abstractmethod
    async def get(self, category_id: str) -> Category | None:
        """Return one category if exists.

        Args:
            category_id [str]: Value supplied to get.

        Returns:
            Category | None: Value produced by get.
        """

    @abstractmethod
    async def update_name(self, category_id: str, *, name: str) -> Category:
        """Update a category name.

        Args:
            category_id [str]: Value supplied to update_name.
            name [str]: Value supplied to update_name.

        Returns:
            Category: Value produced by update_name.
        """

    @abstractmethod
    async def move(
        self,
        category_id: str,
        *,
        parent_id: str | None,
        position: int,
    ) -> Category:
        """Move a category to another parent and position.

        Args:
            category_id [str]: Value supplied to move.
            parent_id [str | None]: Value supplied to move.
            position [int]: Value supplied to move.

        Returns:
            Category: Value produced by move.
        """

    @abstractmethod
    async def reorder(self, *, category_id: str, position: int) -> Category:
        """Update sibling position only.

        Args:
            category_id [str]: Value supplied to reorder.
            position [int]: Value supplied to reorder.

        Returns:
            Category: Value produced by reorder.
        """

    @abstractmethod
    async def delete(self, category_id: str) -> None:
        """Delete category and children cascade behavior.

        Args:
            category_id [str]: Value supplied to delete.
        """

    @abstractmethod
    async def build_tree(self) -> list[Category]:
        """Return a deterministic tree-ordered traversal from roots.

        Returns:
            list[Category]: Value produced by build_tree.
        """

    @abstractmethod
    async def descendants_of(self, category_id: str) -> list[Category]:
        """Return recursive descendants as raw list.

        Args:
            category_id [str]: Value supplied to descendants_of.

        Returns:
            list[Category]: Value produced by descendants_of.
        """

    @abstractmethod
    async def max_depth(self, category_id: str) -> int:
        """Return depth of a category from root (root = 0).

        Args:
            category_id [str]: Value supplied to max_depth.

        Returns:
            int: Value produced by max_depth.
        """

    @abstractmethod
    async def count_items(self, category_id: str) -> int:
        """Return number of direct items in category.

        Args:
            category_id [str]: Value supplied to count_items.

        Returns:
            int: Value produced by count_items.
        """

    @abstractmethod
    async def has_descendant(self, ancestor_id: str, node_id: str) -> bool:
        """Check whether ``node_id`` is in ``ancestor_id`` subtree.

        Args:
            ancestor_id [str]: Value supplied to has_descendant.
            node_id [str]: Value supplied to has_descendant.

        Returns:
            bool: Value produced by has_descendant.
        """
