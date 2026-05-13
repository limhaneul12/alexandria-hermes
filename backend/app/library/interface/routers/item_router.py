"""Generic item routes."""

from __future__ import annotations

from app.library.application.item_service import ItemService
from app.library.domain.entities.enums import ItemType
from app.library.interface.routers._helpers import build_patch_payload
from app.library.interface.routers.dependencies import get_item_service
from app.library.interface.schemas.item_schema import (
    ItemCreateRequest,
    ItemResponse,
    ItemUpdateRequest,
)
from app.shared.exceptions import LibraryResourceNotFoundError
from fastapi import APIRouter, Depends, HTTPException, Query, status

router = APIRouter(prefix="/items", tags=["items"])


@router.post("", response_model=ItemResponse, status_code=status.HTTP_201_CREATED)
async def create_item(
    request: ItemCreateRequest,
    service: ItemService = Depends(get_item_service),
) -> ItemResponse:
    """Create a generic library item."""
    result = await service.create_item(
        item_type=request.item_type,
        title=request.title,
        summary=request.summary,
        content=request.content,
        category_id=request.category_id,
        tags=request.tags,
        status=request.status,
        source_type=request.source_type,
        created_by_type=request.created_by_type,
        created_by_name=request.created_by_name,
        details=request.details,
    )
    return ItemResponse.model_validate(result)


@router.get("/{item_id}", response_model=ItemResponse)
async def get_item(
    item_id: str,
    service: ItemService = Depends(get_item_service),
) -> ItemResponse:
    """Get one generic item."""
    try:
        payload = await service.get_item(item_id)
    except LibraryResourceNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    return ItemResponse.model_validate(payload)


@router.patch("/{item_id}", response_model=ItemResponse)
async def patch_item(
    item_id: str,
    request: ItemUpdateRequest,
    service: ItemService = Depends(get_item_service),
) -> ItemResponse:
    """Patch item metadata/details."""
    patch_payload = build_patch_payload(request.model_dump())

    try:
        payload = await service.update_item(item_id, payload=patch_payload)
    except LibraryResourceNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    return ItemResponse.model_validate(payload)


@router.get("", response_model=list[ItemResponse])
async def list_items(
    item_type: ItemType | None = Query(default=None),
    category_id: str | None = Query(default=None),
    q: str | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
    service: ItemService = Depends(get_item_service),
) -> list[ItemResponse]:
    """List items with optional filters."""
    payloads, _ = await service.list_items(
        item_type=item_type,
        limit=limit,
        offset=offset,
        category_id=category_id,
        search_query=q,
    )
    return [ItemResponse.model_validate(payload) for payload in payloads]


@router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_item(
    item_id: str,
    service: ItemService = Depends(get_item_service),
) -> None:
    """Delete item."""
    try:
        await service.delete_item(item_id)
    except LibraryResourceNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
