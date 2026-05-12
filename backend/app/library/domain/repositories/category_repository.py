"""Category repository abstraction."""

from __future__ import annotations

from abc import ABC, abstractmethod

from app.library.domain.entities.read_models import Category


class CategoryRepository(ABC):
    """Persistence contract for category operations."""

    @abstractmethod
    async def list_all(self) -> list[Category]:
        """Return all categories ordered by display position."""

    @abstractmethod
    async def create(self, *, name: str, parent_id: int | None = None) -> Category:
        """Create a new category node."""

    @abstractmethod
    async def get(self, category_id: int) -> Category | None:
        """Return one category if exists."""

    @abstractmethod
    async def update_name(self, category_id: int, *, name: str) -> Category:
        """Update a category name."""

    @abstractmethod
    async def move(
        self,
        category_id: int,
        *,
        parent_id: int | None,
        position: int,
    ) -> Category:
        """Move a category to another parent and position."""

    @abstractmethod
    async def reorder(self, *, category_id: int, position: int) -> Category:
        """Update sibling position only."""

    @abstractmethod
    async def delete(self, category_id: int) -> None:
        """Delete category and children cascade behavior."""

    @abstractmethod
    async def build_tree(self) -> list[Category]:
        """Return a deterministic tree-ordered traversal from roots."""

    @abstractmethod
    async def descendants_of(self, category_id: int) -> list[Category]:
        """Return recursive descendants as raw list."""

    @abstractmethod
    async def max_depth(self, category_id: int) -> int:
        """Return depth of a category from root (root = 0)."""

    @abstractmethod
    async def count_items(self, category_id: int) -> int:
        """Return number of direct items in category."""

    @abstractmethod
    async def has_descendant(self, ancestor_id: int, node_id: int) -> bool:
        """Check whether ``node_id`` is in ``ancestor_id`` subtree."""
