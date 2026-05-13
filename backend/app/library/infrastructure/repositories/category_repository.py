"""SQLAlchemy implementation of category repository operations."""

from __future__ import annotations

from datetime import UTC, datetime

from app.library.domain.entities.read_models import Category
from app.library.domain.repositories.category_repository import CategoryRepository
from app.library.infrastructure.models.category import CategoryORM
from app.library.infrastructure.models.item import LibraryItemORM
from app.shared.exceptions import NotFoundError
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession


def _to_read_model(row: CategoryORM) -> Category:
    """Map a category ORM row into the domain read model."""
    return Category(
        id=row.id,
        name=row.name,
        parent_id=row.parent_id,
        position=row.position,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


class SqlAlchemyCategoryRepository(CategoryRepository):
    """Category persistence with adjacency-list hierarchy."""

    def __init__(self, *, session: AsyncSession) -> None:
        """Initialize repository.

        Args:
            session: Active async session.

        Return:
            None.
        """
        self._session = session

    async def list_all(self) -> list[Category]:
        """Return all categories ordered by parent and position.

        Args:
            None.

        Return:
            Ordered category rows.
        """
        rows = await self._session.execute(
            select(CategoryORM).order_by(CategoryORM.parent_id, CategoryORM.position),
        )
        return [_to_read_model(row) for row in rows.scalars().all()]

    async def create(self, *, name: str, parent_id: str | None = None) -> Category:
        """Create category node with next sibling position.

        Args:
            name: Display name.
            parent_id: Parent category id.

        Return:
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
        return _to_read_model(model)

    async def get(self, category_id: str) -> Category | None:
        """Get one category by primary key.

        Args:
            category_id: Target id.

        Return:
            Category row or ``None``.
        """
        model = await self._session.get(CategoryORM, category_id)
        return None if model is None else _to_read_model(model)

    async def update_name(self, category_id: str, *, name: str) -> Category:
        """Rename category by primary key.

        Args:
            category_id: Target id.
            name: New display name.

        Return:
            Updated category row.
        """
        model = await self._session.get(CategoryORM, category_id)
        if model is None:
            raise NotFoundError(f"Category not found: {category_id}")

        model.name = name
        model.updated_at = datetime.now(UTC)
        await self._session.flush()
        return _to_read_model(model)

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

        Return:
            Updated category row.
        """
        model = await self._session.get(CategoryORM, category_id)
        if model is None:
            raise NotFoundError(f"Category not found: {category_id}")

        model.parent_id = parent_id
        model.position = position
        model.updated_at = datetime.now(UTC)
        await self._session.flush()
        return _to_read_model(model)

    async def reorder(self, *, category_id: str, position: int) -> Category:
        """Reorder one node in sibling list.

        Args:
            category_id: Target id.
            position: New position value.

        Return:
            Updated category row.
        """
        model = await self._session.get(CategoryORM, category_id)
        if model is None:
            raise NotFoundError(f"Category not found: {category_id}")

        model.position = position
        model.updated_at = datetime.now(UTC)
        await self._session.flush()
        return _to_read_model(model)

    async def delete(self, category_id: str) -> None:
        """Delete one category and all descendants through DB cascade.

        Args:
            category_id: Target id.

        Return:
            None.
        """
        model = await self._session.get(CategoryORM, category_id)
        if model is None:
            raise NotFoundError(f"Category not found: {category_id}")

        await self._session.execute(
            delete(CategoryORM).where(CategoryORM.id == category_id),
        )
        await self._session.flush()

    async def build_tree(self) -> list[Category]:
        """Return categories ordered as ordered-adjacency flat traversal.

        Args:
            None.

        Return:
            All categories ordered by root/position.
        """
        return await self.list_all()

    async def descendants_of(self, category_id: str) -> list[Category]:
        """Traverse descendants by iterative parent-id walk.

        Args:
            category_id: Ancestor id.

        Return:
            Descendant rows in nearest order.
        """
        all_nodes = await self.list_all()
        children_map: dict[str | None, list[Category]] = {}
        for node in all_nodes:
            children_map.setdefault(node.parent_id, []).append(node)

        descendants: list[Category] = []
        queue = [category_id]
        while queue:
            current = queue.pop(0)
            direct = children_map.get(current, [])
            descendants.extend(direct)
            queue.extend(node.id for node in direct)
        return descendants

    async def max_depth(self, category_id: str) -> int:
        """Compute depth from the root node.

        Args:
            category_id: Target id.

        Return:
            Zero-based depth.
        """
        depth = 0
        node = await self.get(category_id)
        while node is not None and node.parent_id is not None:
            depth += 1
            node = await self.get(node.parent_id)
        return depth

    async def count_items(self, category_id: str) -> int:
        """Count directly attached items in category.

        Args:
            category_id: Category id.

        Return:
            Number of direct items.
        """
        return int(
            await self._session.scalar(
                select(func.count(LibraryItemORM.id)).where(
                    LibraryItemORM.category_id == category_id,
                ),
            )
            or 0
        )

    async def has_descendant(self, ancestor_id: str, node_id: str) -> bool:
        """Return true when ``node_id`` is in ``ancestor_id`` subtree.

        Args:
            ancestor_id: Candidate ancestor.
            node_id: Node id to check.

        Return:
            ``True`` when node is descendant.
        """
        descendants = await self.descendants_of(ancestor_id)
        return any(item.id == node_id for item in descendants)
