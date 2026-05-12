"""Usage tracking and analytics routes."""

from __future__ import annotations

from datetime import UTC, datetime

from app.library.application.usage_service import UsageService
from app.library.interface.routers.dependencies import get_usage_service
from app.library.interface.schemas.usage_schema import (
    PopularByCategoryResponse,
    PopularItemResponse,
    UsageRecordRequest,
    UsageRecordResponse,
)
from fastapi import APIRouter, Depends, Query, status

router = APIRouter(prefix="/usage", tags=["usage"])


@router.post(
    "", response_model=UsageRecordResponse, status_code=status.HTTP_201_CREATED
)
async def record_usage(
    request: UsageRecordRequest,
    usage_service: UsageService = Depends(get_usage_service),
) -> UsageRecordResponse:
    """Record one usage event."""
    payload = await usage_service.record_usage(
        {
            "item_id": request.item_id,
            "item_type": request.item_type,
            "agent_name": request.agent_name,
            "librarian_provider": request.librarian_provider,
            "query": request.query,
            "selection_source": request.selection_source,
            "used_at": datetime.now(UTC),
            "success": request.success,
            "feedback": request.feedback,
        }
    )
    return UsageRecordResponse.model_validate(payload)


@router.get("/recent", response_model=list[UsageRecordResponse])
async def recent_usage(
    limit: int = Query(default=20, ge=1, le=200),
    usage_service: UsageService = Depends(get_usage_service),
) -> list[UsageRecordResponse]:
    """Return recent usage events."""
    rows = await usage_service.recent(limit=limit)
    return [UsageRecordResponse.model_validate(row) for row in rows]


@router.get("/popular", response_model=list[PopularItemResponse])
async def popular_items(
    limit: int = Query(default=10, ge=1, le=100),
    usage_service: UsageService = Depends(get_usage_service),
) -> list[PopularItemResponse]:
    """Return popular items ranked by usage count."""
    return [
        PopularItemResponse.model_validate(row)
        for row in await usage_service.popular(limit=limit)
    ]


@router.get("/popular/by-category", response_model=list[PopularByCategoryResponse])
async def popular_by_category(
    limit: int = Query(default=10, ge=1, le=100),
    usage_service: UsageService = Depends(get_usage_service),
) -> list[PopularByCategoryResponse]:
    """Return category-level usage ranking."""
    return [
        PopularByCategoryResponse.model_validate(row)
        for row in await usage_service.popular_by_category(limit=limit)
    ]


@router.get("/items/{item_id}", response_model=list[UsageRecordResponse])
async def item_usage(
    item_id: int,
    usage_service: UsageService = Depends(get_usage_service),
) -> list[UsageRecordResponse]:
    """Get all usage rows for one item."""
    return [
        UsageRecordResponse.model_validate(row)
        for row in await usage_service.by_item(item_id)
    ]
