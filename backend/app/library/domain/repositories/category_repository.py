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
    async def create(self, *, name: str, parent_id: str | None = None) -> Category:
        """Create a new category node."""

    @abstractmethod
    async def get(self, category_id: str) -> Category | None:
        """Return one category if exists."""

    @abstractmethod
    async def update_name(self, category_id: str, *, name: str) -> Category:
        """Update a category name."""

    @abstractmethod
    async def move(
        self,
        category_id: str,
        *,
        parent_id: str | None,
        position: int,
    ) -> Category:
        """Move a category to another parent and position."""

    @abstractmethod
    async def reorder(self, *, category_id: str, position: int) -> Category:
        """Update sibling position only."""

    @abstractmethod
    async def delete(self, category_id: str) -> None:
        """Delete category and children cascade behavior."""

    @abstractmethod
    async def build_tree(self) -> list[Category]:
        """Return a deterministic tree-ordered traversal from roots."""

    @abstractmethod
    async def descendants_of(self, category_id: str) -> list[Category]:
        """Return recursive descendants as raw list."""

    @abstractmethod
    async def max_depth(self, category_id: str) -> int:
        """Return depth of a category from root (root = 0)."""

    @abstractmethod
    async def count_items(self, category_id: str) -> int:
        """Return number of direct items in category."""

    @abstractmethod
    async def has_descendant(self, ancestor_id: str, node_id: str) -> bool:
        """Check whether ``node_id`` is in ``ancestor_id`` subtree."""
