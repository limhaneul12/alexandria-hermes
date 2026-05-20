"""Category ORM/read-model mapping."""

from __future__ import annotations

from app.library.domain.entities.read_models import Category
from app.library.infrastructure.models.category_models import CategoryORM
from app.shared.types.types_convert_utils import aware_utc_datetime


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
        created_at=aware_utc_datetime(row.created_at),
        updated_at=aware_utc_datetime(row.updated_at),
    )
    return read_model
