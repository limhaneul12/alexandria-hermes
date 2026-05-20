"""Service use cases for category management."""

from __future__ import annotations

from app.library.domain.entities.read_models import Category
from app.library.domain.repositories.category_repository import ICategoryRepository
from app.shared.exceptions import (
    LibraryCategoryCycleError,
    LibraryResourceNotFoundError,
    LibraryValidationError,
)


class CategoryService:
    """Category service object."""

    def __init__(
        self,
        category_repo: ICategoryRepository,
        max_depth: int = 10,
    ) -> None:
        """Initialize category service dependencies."""
        self.category_repo = category_repo
        self.max_depth = max_depth

    async def create_category(
        self,
        name: str,
        parent_id: str | None = None,
    ) -> Category:
        """Create a category and validate parent exists.

        Args:
            name: Name used by clients.
            parent_id: Optional parent category id.

        Returns:
            Created category row.
        """
        if parent_id is not None and await self.category_repo.get(parent_id) is None:
            raise LibraryValidationError(f"Parent category does not exist: {parent_id}")
        return await self.category_repo.create(name=name, parent_id=parent_id)

    async def list_categories(self) -> list[Category]:
        """Return all categories ordered by parent and position.

        Args:
            None.

        Returns:
            Category rows.
        """
        return await self.category_repo.list_all()

    async def get_category(self, category_id: str) -> Category | None:
        """Read one category by id.

        Args:
            category_id: Target id.

        Returns:
            Category row or ``None``.
        """
        return await self.category_repo.get(category_id)

    async def update_category(self, category_id: str, name: str) -> Category:
        """Rename one category.

        Args:
            category_id: Target id.
            name: New name.

        Returns:
            Updated category row.
        """
        row = await self.category_repo.update_name(category_id, name=name)
        return row

    async def move_category(
        self,
        category_id: str,
        parent_id: str | None,
        position: int,
    ) -> Category:
        """Move category and guard against hierarchy loops.

        Args:
            category_id: Target id.
            parent_id: New parent id (or ``None``).
            position: New sibling position.

        Returns:
            Updated category row.
        """
        if category_id == parent_id:
            raise LibraryCategoryCycleError("Category cannot be moved under itself")

        if parent_id is not None:
            if parent_id == category_id:
                raise LibraryCategoryCycleError("Category cannot move under itself")

            if await self.category_repo.has_descendant(category_id, parent_id):
                raise LibraryCategoryCycleError("Category move creates cycle")

            if await self.category_repo.get(parent_id) is None:
                raise LibraryValidationError(
                    f"Parent category does not exist: {parent_id}"
                )

        max_depth = await self._max_depth_after_move(
            category_id=category_id,
            parent_id=parent_id,
        )
        if max_depth > self.max_depth:
            raise LibraryValidationError("Category depth exceeds allowed maximum")

        return await self.category_repo.move(
            category_id,
            parent_id=parent_id,
            position=position,
        )

    async def reorder_category(self, category_id: str, position: int) -> Category:
        """Re-order category among siblings.

        Args:
            category_id: Target id.
            position: New position.

        Returns:
            Updated category row.
        """
        return await self.category_repo.reorder(
            category_id=category_id, position=position
        )

    async def delete_category(self, category_id: str) -> None:
        """Delete a category and dependent subtree.

        Args:
            category_id: Target id.

        Returns:
            None.
        """
        if await self.category_repo.get(category_id) is None:
            raise LibraryResourceNotFoundError(f"Category not found: {category_id}")
        await self.category_repo.delete(category_id)

    async def tree(self) -> list[Category]:
        """Return deterministic tree-ordered list.

        Args:
            None.

        Returns:
            All category rows.
        """
        return await self.category_repo.build_tree()

    async def _max_depth_after_move(
        self,
        category_id: str,
        parent_id: str | None,
    ) -> int:
        """Estimate max depth after move operation.

        Args:
            category_id: Source id.
            parent_id: New parent id.

        Returns:
            Resulting maximum depth.
        """
        if parent_id is None:
            return 0

        parent_depth = await self.category_repo.max_depth(parent_id)
        children_depth = await self._subtree_depth(category_id)
        return parent_depth + 1 + children_depth

    async def _subtree_depth(self, root_id: str) -> int:
        """Compute subtree depth of one category.

        Args:
            root_id: Root node id.

        Returns:
            Maximum child depth.
        """
        # Lightweight approximation for small trees.
        descendants = await self.category_repo.descendants_of(root_id)
        if not descendants:
            return 0
        max_depth = 0
        for child in descendants:
            child_depth = await self.category_repo.max_depth(child.id)
            root_depth = await self.category_repo.max_depth(root_id)
            if child_depth - root_depth > max_depth:
                max_depth = child_depth - root_depth
        return max_depth
