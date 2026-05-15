"""Usage tracking and analytics routes."""

from __future__ import annotations

from datetime import UTC, datetime

from app.container import ApplicationContainer
from app.library.application.usage_service import UsageService
from app.library.interface.schemas.usage.usage_schema import (
    PopularByCategoryResponseList,
    PopularItemResponseList,
    UsageRecordRequest,
    UsageRecordResponse,
    UsageRecordResponseList,
)
from app.shared.exceptions.exception_decorators import router_exception_status
from app.shared.exceptions.route_exceptions import LIBRARY_ROUTE_EXCEPTION_MAPPING
from dependency_injector.wiring import Provide, inject
from fastapi import APIRouter, Depends, Query, status

router = APIRouter(prefix="/library/usage", tags=["usage"])


@router.post(
    "",
    response_model=UsageRecordResponse,
    status_code=status.HTTP_201_CREATED,
    description="Library API operation.",
    summary="Record usage",
)
@router_exception_status(LIBRARY_ROUTE_EXCEPTION_MAPPING)
@inject
async def record_usage(
    request: UsageRecordRequest,
    usage_service: UsageService = Depends(
        Provide[ApplicationContainer.library.usage_service]
    ),
) -> UsageRecordResponse:
    """Record one usage event.

    Args:
        request [UsageRecordRequest]: Value supplied to record_usage.
        usage_service [UsageService]: Value supplied to record_usage.

    Returns:
        UsageRecordResponse: Value produced by record_usage.
    """
    payload = await usage_service.record_usage(request.to_payload(datetime.now(UTC)))
    validation = UsageRecordResponse.model_validate(payload)
    return validation


@router.get(
    "/recent",
    response_model=UsageRecordResponseList,
    description="Library API operation.",
    status_code=status.HTTP_200_OK,
    summary="Recent usage",
)
@router_exception_status(LIBRARY_ROUTE_EXCEPTION_MAPPING)
@inject
async def recent_usage(
    limit: int = Query(default=20, ge=1, le=200),
    usage_service: UsageService = Depends(
        Provide[ApplicationContainer.library.usage_service]
    ),
) -> UsageRecordResponseList:
    """Return recent usage events.

    Args:
        limit [int]: Value supplied to recent_usage.
        usage_service [UsageService]: Value supplied to recent_usage.

    Returns:
        UsageRecordResponseList: Value produced by recent_usage.
    """
    rows = await usage_service.recent(limit=limit)
    validation = UsageRecordResponseList.model_validate(rows)
    return validation


@router.get(
    "/popular",
    response_model=PopularItemResponseList,
    description="Library API operation.",
    status_code=status.HTTP_200_OK,
    summary="Popular items",
)
@router_exception_status(LIBRARY_ROUTE_EXCEPTION_MAPPING)
@inject
async def popular_items(
    limit: int = Query(default=10, ge=1, le=100),
    usage_service: UsageService = Depends(
        Provide[ApplicationContainer.library.usage_service]
    ),
) -> PopularItemResponseList:
    """Return popular items ranked by usage count.

    Args:
        limit [int]: Value supplied to popular_items.
        usage_service [UsageService]: Value supplied to popular_items.

    Returns:
        PopularItemResponseList: Value produced by popular_items.
    """
    rows = await usage_service.popular(limit=limit)
    validation = PopularItemResponseList.model_validate(rows)
    return validation


@router.get(
    "/popular/by-category",
    response_model=PopularByCategoryResponseList,
    description="Library API operation.",
    status_code=status.HTTP_200_OK,
    summary="Popular by category",
)
@router_exception_status(LIBRARY_ROUTE_EXCEPTION_MAPPING)
@inject
async def popular_by_category(
    limit: int = Query(default=10, ge=1, le=100),
    usage_service: UsageService = Depends(
        Provide[ApplicationContainer.library.usage_service]
    ),
) -> PopularByCategoryResponseList:
    """Return category-level usage ranking.

    Args:
        limit [int]: Value supplied to popular_by_category.
        usage_service [UsageService]: Value supplied to popular_by_category.

    Returns:
        PopularByCategoryResponseList: Value produced by popular_by_category.
    """
    rows = await usage_service.popular_by_category(limit=limit)
    validation = PopularByCategoryResponseList.model_validate(rows)
    return validation


@router.get(
    "/library/items/{item_id}",
    response_model=UsageRecordResponseList,
    description="Library API operation.",
    status_code=status.HTTP_200_OK,
    summary="Item usage",
)
@router_exception_status(LIBRARY_ROUTE_EXCEPTION_MAPPING)
@inject
async def item_usage(
    item_id: str,
    usage_service: UsageService = Depends(
        Provide[ApplicationContainer.library.usage_service]
    ),
) -> UsageRecordResponseList:
    """Get all usage rows for one item.

    Args:
        item_id [str]: Value supplied to item_usage.
        usage_service [UsageService]: Value supplied to item_usage.

    Returns:
        UsageRecordResponseList: Value produced by item_usage.
    """
    rows = await usage_service.by_item(item_id)
    validation = UsageRecordResponseList.model_validate(rows)
    return validation
