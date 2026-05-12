"""Category routes."""

from __future__ import annotations

from collections import defaultdict

from app.library.application.category_service import CategoryService
from app.library.domain.entities.read_models import Category
from app.library.interface.routers.dependencies import (
    get_category_service,
)
from app.library.interface.schemas.category_schema import (
    CategoryCreateRequest,
    CategoryMoveRequest,
    CategoryResponse,
    CategoryTreeNode,
    CategoryUpdateRequest,
)
from app.shared.exceptions import (
    LibraryCategoryCycleError,
    LibraryResourceNotFoundError,
    LibraryValidationError,
)
from fastapi import APIRouter, Depends, HTTPException, status

router = APIRouter(prefix="/categories", tags=["categories"])


def _to_tree_node(
    row_map: dict[int | None, list[Category]],
) -> list[CategoryTreeNode]:
    """Build nested tree nodes from flattened rows.

    Args:
        row_map: Parent id -> child rows.

    Return:
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


@router.post("", response_model=CategoryResponse, status_code=status.HTTP_201_CREATED)
async def create_category(
    request: CategoryCreateRequest,
    service: CategoryService = Depends(get_category_service),
) -> CategoryResponse:
    """Create category with optional parent."""
    try:
        category = await service.create_category(
            name=request.name,
            parent_id=request.parent_id,
        )
    except LibraryValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    return CategoryResponse.model_validate(category)


@router.get("", response_model=list[CategoryResponse])
async def list_categories(
    service: CategoryService = Depends(get_category_service),
) -> list[CategoryResponse]:
    """List categories with adjacency list ordering."""
    return [
        CategoryResponse.model_validate(row) for row in await service.list_categories()
    ]


@router.get("/tree", response_model=list[CategoryTreeNode])
async def get_category_tree(
    service: CategoryService = Depends(get_category_service),
) -> list[CategoryTreeNode]:
    """Return hierarchy as nested JSON."""
    categories = await service.tree()
    grouped: dict[int | None, list[Category]] = defaultdict(list)
    for row in categories:
        grouped[row.parent_id].append(row)
    for rows in grouped.values():
        rows.sort(key=lambda item: item.position)
    return _to_tree_node(grouped)


@router.get("/{category_id}", response_model=CategoryResponse)
async def get_category(
    category_id: int,
    service: CategoryService = Depends(get_category_service),
) -> CategoryResponse:
    """Get one category by id."""
    category = await service.get_category(category_id)
    if category is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Category not found",
        )
    return CategoryResponse.model_validate(category)


@router.patch("/{category_id}", response_model=CategoryResponse)
async def update_category(
    category_id: int,
    request: CategoryUpdateRequest,
    service: CategoryService = Depends(get_category_service),
) -> CategoryResponse:
    """Rename category."""
    try:
        category = await service.update_category(category_id, name=request.name)
    except LibraryResourceNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    return CategoryResponse.model_validate(category)


@router.patch("/{category_id}/move", response_model=CategoryResponse)
async def move_category(
    category_id: int,
    request: CategoryMoveRequest,
    service: CategoryService = Depends(get_category_service),
) -> CategoryResponse:
    """Move category to a new parent and position."""
    try:
        category = await service.move_category(
            category_id,
            parent_id=request.parent_id,
            position=request.position,
        )
    except LibraryCategoryCycleError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc
    except LibraryValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except LibraryResourceNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    return CategoryResponse.model_validate(category)


@router.delete("/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_category(
    category_id: int,
    service: CategoryService = Depends(get_category_service),
) -> None:
    """Delete category and descendants."""
    try:
        await service.delete_category(category_id)
    except LibraryResourceNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
