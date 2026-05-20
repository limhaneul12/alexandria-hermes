"""Generic item routes."""

from __future__ import annotations

from app.container import ApplicationContainer
from app.library.application.item_service import ItemService
from app.library.domain.event_enum.item_enums import ItemType
from app.library.interface.routers._helpers import build_patch_payload
from app.library.interface.schemas.item.item_schema import (
    ItemResponse,
    ItemResponseList,
    ItemUpdateRequest,
)
from app.shared.exceptions import LibraryValidationError
from app.shared.exceptions.exception_decorators import router_exception_status
from app.shared.exceptions.route_exceptions import LIBRARY_ROUTE_EXCEPTION_MAPPING
from dependency_injector.wiring import Provide, inject
from fastapi import APIRouter, Depends, Query, status

router = APIRouter(prefix="/library/items", tags=["items"])


@router.get(
    "/{item_id}",
    response_model=ItemResponse,
    description="Library API operation.",
    status_code=status.HTTP_200_OK,
    summary="Get item",
)
@router_exception_status(LIBRARY_ROUTE_EXCEPTION_MAPPING)
@inject
async def get_item(
    item_id: str,
    service: ItemService = Depends(Provide[ApplicationContainer.library.item_service]),
) -> ItemResponse:
    """Get one generic item.

    Args:
        item_id [str]: Value supplied to get_item.
        service [ItemService]: Value supplied to get_item.

    Returns:
        ItemResponse: Value produced by get_item.
    """
    payload = await service.get_item(item_id)
    validation = ItemResponse.model_validate(payload)
    return validation


@router.patch(
    "/{item_id}",
    response_model=ItemResponse,
    description="Library API operation.",
    status_code=status.HTTP_200_OK,
    summary="Patch item",
)
@router_exception_status(LIBRARY_ROUTE_EXCEPTION_MAPPING)
@inject
async def patch_item(
    item_id: str,
    request: ItemUpdateRequest,
    service: ItemService = Depends(Provide[ApplicationContainer.library.item_service]),
) -> ItemResponse:
    """Patch item metadata/details.

    Args:
        item_id [str]: Value supplied to patch_item.
        request [ItemUpdateRequest]: Value supplied to patch_item.
        service [ItemService]: Value supplied to patch_item.

    Returns:
        ItemResponse: Value produced by patch_item.
    """
    patch_payload = build_patch_payload(request.model_dump())

    payload = await service.update_item(item_id, payload=patch_payload)
    validation = ItemResponse.model_validate(payload)
    return validation


@router.get(
    "",
    response_model=ItemResponseList,
    description=(
        "List library items. Text search is intentionally handled by "
        "/library/search so list routes never run LIKE scans over item content."
    ),
    status_code=status.HTTP_200_OK,
    summary="List items",
)
@router_exception_status(LIBRARY_ROUTE_EXCEPTION_MAPPING)
@inject
async def list_items(
    item_type: ItemType | None = Query(default=None),
    category_id: str | None = Query(default=None),
    q: str | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
    service: ItemService = Depends(Provide[ApplicationContainer.library.item_service]),
) -> ItemResponseList:
    """List items with optional filters.

    Args:
        item_type [ItemType | None]: Value supplied to list_items.
        category_id [str | None]: Value supplied to list_items.
        q [str | None]: Value supplied to list_items.
        limit [int]: Value supplied to list_items.
        offset [int]: Value supplied to list_items.
        service [ItemService]: Value supplied to list_items.

    Returns:
        ItemResponseList: Value produced by list_items.
    """
    if q is not None and q.strip():
        raise LibraryValidationError("Use /library/search for text search.")
    payloads, _ = await service.list_items(
        item_type=item_type,
        limit=limit,
        offset=offset,
        category_id=category_id,
    )
    validation = ItemResponseList.model_validate(payloads)
    return validation


@router.delete(
    "/{item_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    description="Library API operation.",
    summary="Delete item",
)
@router_exception_status(LIBRARY_ROUTE_EXCEPTION_MAPPING)
@inject
async def delete_item(
    item_id: str,
    service: ItemService = Depends(Provide[ApplicationContainer.library.item_service]),
) -> None:
    """Delete item.

    Args:
        item_id [str]: Value supplied to delete_item.
        service [ItemService]: Value supplied to delete_item.
    """
    await service.delete_item(item_id)
