"""Category ORM/read-model mapping."""

from __future__ import annotations

from app.library.domain.entities.read_models import Category
from app.library.infrastructure.models.category_models import CategoryORM


def category_to_read_model(row: CategoryORM) -> Category:
    """Map a category ORM row into the domain read model.

    Args:
        row: Persisted category row.

    Returns:
        Category read model.
    """
    read_model = Category(
        id=row.id,
        name=row.name,
        parent_id=row.parent_id,
        position=row.position,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )
    return read_model
