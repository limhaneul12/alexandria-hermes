"""SQLAlchemy implementation of category repository operations."""

from __future__ import annotations

from datetime import UTC, datetime

from app.library.domain.entities.read_models import Category
from app.library.domain.repositories.category_repository import ICategoryRepository
from app.library.infrastructure.models.category_models import CategoryORM
from app.library.infrastructure.models.item_models import LibraryItemORM
from app.library.infrastructure.repositories.categories.hierarchy import (
    descendants_of as hierarchy_descendants_of,
    has_descendant as hierarchy_has_descendant,
    max_depth as hierarchy_max_depth,
)
from app.library.infrastructure.repositories.categories.mapper import (
    category_to_read_model,
)
from app.shared.exceptions import LibraryResourceNotFoundError
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession


class SqlAlchemyCategoryRepository(ICategoryRepository):
    """Category persistence with adjacency-list hierarchy."""

    def __init__(self, *, session: AsyncSession) -> None:
        """Initialize repository.

        Args:
            session: Active async session.

        Returns:
            None.
        """
        self._session = session

    async def list_all(self) -> list[Category]:
        """Return all categories ordered by parent and position.

        Args:
            None.

        Returns:
            Ordered category rows.
        """
        rows = await self._session.execute(
            select(CategoryORM).order_by(CategoryORM.parent_id, CategoryORM.position),
        )
        categories = [category_to_read_model(row) for row in rows.scalars().all()]
        return categories

    async def create(self, *, name: str, parent_id: str | None = None) -> Category:
        """Create category node with next sibling position.

        Args:
            name: Display name.
            parent_id: Parent category id.

        Returns:
            Created category row.
        """
        max_position = await self._session.scalar(
            select(func.coalesce(func.max(CategoryORM.position), 0)).where(
                CategoryORM.parent_id.is_(parent_id),
            ),
        )
        if max_position is None:
            max_position = 0

        now = datetime.now(UTC)
        model = CategoryORM(
            name=name,
            parent_id=parent_id,
            position=max_position + 1,
            created_at=now,
            updated_at=now,
        )
        self._session.add(model)
        await self._session.flush()
        category = category_to_read_model(model)
        return category

    async def get(self, category_id: str) -> Category | None:
        """Get one category by primary key.

        Args:
            category_id: Target id.

        Returns:
            Category row or ``None``.
        """
        model = await self._session.get(CategoryORM, category_id)
        category = None if model is None else category_to_read_model(model)
        return category

    async def update_name(self, category_id: str, *, name: str) -> Category:
        """Rename category by primary key.

        Args:
            category_id: Target id.
            name: New display name.

        Returns:
            Updated category row.
        """
        model = await self._session.get(CategoryORM, category_id)
        if model is None:
            raise LibraryResourceNotFoundError(f"Category not found: {category_id}")

        model.name = name
        model.updated_at = datetime.now(UTC)
        await self._session.flush()
        category = category_to_read_model(model)
        return category

    async def move(
        self,
        category_id: str,
        *,
        parent_id: str | None,
        position: int,
    ) -> Category:
        """Move category and set position.

        Args:
            category_id: Target id.
            parent_id: New parent id (or ``None`` for root).
            position: New sibling order.

        Returns:
            Updated category row.
        """
        model = await self._session.get(CategoryORM, category_id)
        if model is None:
            raise LibraryResourceNotFoundError(f"Category not found: {category_id}")

        model.parent_id = parent_id
        model.position = position
        model.updated_at = datetime.now(UTC)
        await self._session.flush()
        category = category_to_read_model(model)
        return category

    async def reorder(self, *, category_id: str, position: int) -> Category:
        """Reorder one node in sibling list.

        Args:
            category_id: Target id.
            position: New position value.

        Returns:
            Updated category row.
        """
        model = await self._session.get(CategoryORM, category_id)
        if model is None:
            raise LibraryResourceNotFoundError(f"Category not found: {category_id}")

        model.position = position
        model.updated_at = datetime.now(UTC)
        await self._session.flush()
        category = category_to_read_model(model)
        return category

    async def delete(self, category_id: str) -> None:
        """Delete one category and all descendants through DB cascade.

        Args:
            category_id: Target id.

        Returns:
            None.
        """
        model = await self._session.get(CategoryORM, category_id)
        if model is None:
            raise LibraryResourceNotFoundError(f"Category not found: {category_id}")

        await self._session.execute(
            delete(CategoryORM).where(CategoryORM.id == category_id),
        )
        await self._session.flush()

    async def build_tree(self) -> list[Category]:
        """Return categories ordered as ordered-adjacency flat traversal.

        Args:
            None.

        Returns:
            All categories ordered by root/position.
        """
        return await self.list_all()

    async def descendants_of(self, category_id: str) -> list[Category]:
        """Traverse descendants by iterative parent-id walk.

        Args:
            category_id: Ancestor id.

        Returns:
            Descendant rows in nearest order.
        """
        all_nodes = await self.list_all()
        descendants = hierarchy_descendants_of(all_nodes, category_id)
        return descendants

    async def max_depth(self, category_id: str) -> int:
        """Compute depth from the root node.

        Args:
            category_id: Target id.

        Returns:
            Zero-based depth.
        """
        all_nodes = await self.list_all()
        depth = hierarchy_max_depth(all_nodes, category_id)
        return depth

    async def count_items(self, category_id: str) -> int:
        """Count directly attached items in category.

        Args:
            category_id: Category id.

        Returns:
            Number of direct items.
        """
        item_count = int(
            await self._session.scalar(
                select(func.count(LibraryItemORM.id)).where(
                    LibraryItemORM.category_id == category_id,
                ),
            )
            or 0
        )
        return item_count

    async def has_descendant(self, ancestor_id: str, node_id: str) -> bool:
        """Return true when ``node_id`` is in ``ancestor_id`` subtree.

        Args:
            ancestor_id: Candidate ancestor.
            node_id: Node id to check.

        Returns:
            ``True`` when node is descendant.
        """
        all_nodes = await self.list_all()
        descendant_found = hierarchy_has_descendant(all_nodes, ancestor_id, node_id)
        return descendant_found
