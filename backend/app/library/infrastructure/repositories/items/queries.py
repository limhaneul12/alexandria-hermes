"""Query construction helpers for library item repository listing."""

from __future__ import annotations

from app.library.domain.event_enum.item_enums import ItemType
from app.library.infrastructure.models.item_models import LibraryItemORM
from sqlalchemy import Select, func, select


def build_items_by_type_statement(
    *,
    item_type: ItemType,
    limit: int | None = None,
    offset: int = 0,
) -> Select[tuple[LibraryItemORM]]:
    """Build a query for items matching one item type.

    Args:
        item_type [ItemType]: Value supplied to build_items_by_type_statement.
        limit [int | None]: Value supplied to build_items_by_type_statement.
        offset [int]: Value supplied to build_items_by_type_statement.

    Returns:
        Select[tuple[LibraryItemORM]]: Value produced by build_items_by_type_statement.
    """
    statement = select(LibraryItemORM).where(
        LibraryItemORM.item_type == item_type.value
    )
    if limit is not None:
        statement = statement.limit(limit).offset(offset)
    typed_statement = statement
    return typed_statement


def build_items_filtered_statement(
    *,
    category_id: str | None = None,
) -> Select[tuple[LibraryItemORM]]:
    """Build the base item listing statement before ordering/pagination.

    Args:
        category_id [str | None]: Value supplied to build_items_filtered_statement.

    Returns:
        Select[tuple[LibraryItemORM]]: Value produced by build_items_filtered_statement.
    """
    statement = select(LibraryItemORM)
    if category_id is not None:
        statement = statement.where(LibraryItemORM.category_id == category_id)
    filtered_statement = statement
    return filtered_statement


def build_items_page_statement(
    statement: Select[tuple[LibraryItemORM]],
    *,
    limit: int | None = None,
    offset: int = 0,
) -> Select[tuple[LibraryItemORM]]:
    """Apply default ordering and optional pagination to an item listing.

    Args:
        statement [Select[tuple[LibraryItemORM]]]: Value supplied to build_items_page_statement.
        limit [int | None]: Value supplied to build_items_page_statement.
        offset [int]: Value supplied to build_items_page_statement.

    Returns:
        Select[tuple[LibraryItemORM]]: Value produced by build_items_page_statement.
    """
    page_statement = statement.order_by(LibraryItemORM.updated_at.desc())
    if limit is not None:
        page_statement = page_statement.limit(limit).offset(offset)
    return page_statement


def build_items_count_statement(
    statement: Select[tuple[LibraryItemORM]],
) -> Select[tuple[int]]:
    """Build count query for a filtered item listing statement.

    Args:
        statement [Select[tuple[LibraryItemORM]]]: Value supplied to build_items_count_statement.

    Returns:
        Select[tuple[int]]: Value produced by build_items_count_statement.
    """
    count_statement = select(func.count()).select_from(statement.subquery())
    return count_statement
