"""Category routes."""

from __future__ import annotations

from collections import defaultdict

from app.container import ApplicationContainer
from app.library.application.category_service import CategoryService
from app.library.domain.entities.read_models import Category
from app.library.interface.schemas.category.category_schema import (
    CategoryCreateRequest,
    CategoryMoveRequest,
    CategoryResponse,
    CategoryResponseList,
    CategoryTreeNode,
    CategoryTreeResponse,
    CategoryUpdateRequest,
)
from app.shared.exceptions.exception_decorators import router_exception_status
from app.shared.exceptions.route_exceptions import LIBRARY_ROUTE_EXCEPTION_MAPPING
from dependency_injector.wiring import Provide, inject
from fastapi import APIRouter, Depends, HTTPException, status

router = APIRouter(prefix="/library/categories", tags=["categories"])


def _to_tree_node(
    row_map: dict[str | None, list[Category]],
) -> list[CategoryTreeNode]:
    """Build nested tree nodes from flattened rows.

    Args:
        row_map: Parent id -> child rows.

    Returns:
        Tree-shaped response list.
    """

    def _build(current: Category) -> CategoryTreeNode:
        child_rows = row_map.get(current.id, [])
        children = [_build(child) for child in child_rows]
        return CategoryTreeNode(
            id=current.id,
            name=current.name,
            parent_id=current.parent_id,
            position=current.position,
            children=children,
        )

    return [_build(root) for root in row_map.get(None, [])]


@router.post(
    "",
    response_model=CategoryResponse,
    status_code=status.HTTP_201_CREATED,
    description="Library API operation.",
    summary="Create category",
)
@router_exception_status(LIBRARY_ROUTE_EXCEPTION_MAPPING)
@inject
async def create_category(
    request: CategoryCreateRequest,
    service: CategoryService = Depends(
        Provide[ApplicationContainer.library.category_service]
    ),
) -> CategoryResponse:
    """Create category with optional parent.

    Args:
        request [CategoryCreateRequest]: Value supplied to create_category.
        service [CategoryService]: Value supplied to create_category.

    Returns:
        CategoryResponse: Value produced by create_category.
    """
    category = await service.create_category(
        name=request.name,
        parent_id=request.parent_id,
    )
    validation = CategoryResponse.model_validate(category)
    return validation


@router.get(
    "",
    response_model=CategoryResponseList,
    description="Library API operation.",
    status_code=status.HTTP_200_OK,
    summary="List categories",
)
@router_exception_status(LIBRARY_ROUTE_EXCEPTION_MAPPING)
@inject
async def list_categories(
    service: CategoryService = Depends(
        Provide[ApplicationContainer.library.category_service]
    ),
) -> CategoryResponseList:
    """List categories with adjacency list ordering.

    Args:
        service [CategoryService]: Value supplied to list_categories.

    Returns:
        CategoryResponseList: Value produced by list_categories.
    """
    rows = await service.list_categories()
    validation = CategoryResponseList.model_validate(rows)
    return validation


@router.get(
    "/tree",
    response_model=CategoryTreeResponse,
    description="Library API operation.",
    status_code=status.HTTP_200_OK,
    summary="Get category tree",
)
@router_exception_status(LIBRARY_ROUTE_EXCEPTION_MAPPING)
@inject
async def get_category_tree(
    service: CategoryService = Depends(
        Provide[ApplicationContainer.library.category_service]
    ),
) -> CategoryTreeResponse:
    """Return hierarchy as nested JSON.

    Args:
        service [CategoryService]: Value supplied to get_category_tree.

    Returns:
        CategoryTreeResponse: Value produced by get_category_tree.
    """
    categories = await service.tree()
    grouped: dict[str | None, list[Category]] = defaultdict(list)
    for row in categories:
        grouped[row.parent_id].append(row)
    for rows in grouped.values():
        rows.sort(key=lambda item: item.position)
    tree_nodes = _to_tree_node(grouped)
    validation = CategoryTreeResponse.model_validate(tree_nodes)
    return validation


@router.get(
    "/{category_id}",
    response_model=CategoryResponse,
    description="Library API operation.",
    status_code=status.HTTP_200_OK,
    summary="Get category",
)
@router_exception_status(LIBRARY_ROUTE_EXCEPTION_MAPPING)
@inject
async def get_category(
    category_id: str,
    service: CategoryService = Depends(
        Provide[ApplicationContainer.library.category_service]
    ),
) -> CategoryResponse:
    """Get one category by id.

    Args:
        category_id [str]: Value supplied to get_category.
        service [CategoryService]: Value supplied to get_category.

    Returns:
        CategoryResponse: Value produced by get_category.
    """
    category = await service.get_category(category_id)
    if category is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Category not found",
        )
    validation = CategoryResponse.model_validate(category)
    return validation


@router.patch(
    "/{category_id}",
    response_model=CategoryResponse,
    description="Library API operation.",
    status_code=status.HTTP_200_OK,
    summary="Update category",
)
@router_exception_status(LIBRARY_ROUTE_EXCEPTION_MAPPING)
@inject
async def update_category(
    category_id: str,
    request: CategoryUpdateRequest,
    service: CategoryService = Depends(
        Provide[ApplicationContainer.library.category_service]
    ),
) -> CategoryResponse:
    """Rename category.

    Args:
        category_id [str]: Value supplied to update_category.
        request [CategoryUpdateRequest]: Value supplied to update_category.
        service [CategoryService]: Value supplied to update_category.

    Returns:
        CategoryResponse: Value produced by update_category.
    """
    category = await service.update_category(category_id, name=request.name)
    validation = CategoryResponse.model_validate(category)
    return validation


@router.patch(
    "/{category_id}/move",
    response_model=CategoryResponse,
    description="Library API operation.",
    status_code=status.HTTP_200_OK,
    summary="Move category",
)
@router_exception_status(LIBRARY_ROUTE_EXCEPTION_MAPPING)
@inject
async def move_category(
    category_id: str,
    request: CategoryMoveRequest,
    service: CategoryService = Depends(
        Provide[ApplicationContainer.library.category_service]
    ),
) -> CategoryResponse:
    """Move category to a new parent and position.

    Args:
        category_id [str]: Value supplied to move_category.
        request [CategoryMoveRequest]: Value supplied to move_category.
        service [CategoryService]: Value supplied to move_category.

    Returns:
        CategoryResponse: Value produced by move_category.
    """
    category = await service.move_category(
        category_id,
        parent_id=request.parent_id,
        position=request.position,
    )
    validation = CategoryResponse.model_validate(category)
    return validation


@router.delete(
    "/{category_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    description="Library API operation.",
    summary="Delete category",
)
@router_exception_status(LIBRARY_ROUTE_EXCEPTION_MAPPING)
@inject
async def delete_category(
    category_id: str,
    service: CategoryService = Depends(
        Provide[ApplicationContainer.library.category_service]
    ),
) -> None:
    """Delete category and descendants.

    Args:
        category_id [str]: Value supplied to delete_category.
        service [CategoryService]: Value supplied to delete_category.
    """
    await service.delete_category(category_id)
