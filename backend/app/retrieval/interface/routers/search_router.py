"""Search routes backed by SQLite FTS5."""

from __future__ import annotations

from app.container import ApplicationContainer
from app.library.application.item_search_service import ItemSearchService
from app.library.domain.event_enum.item_enums import ItemType
from app.library.interface.schemas.item.item_search_schema import ItemSearchResponse
from app.shared.exceptions.exception_decorators import router_exception_status
from app.shared.exceptions.route_exceptions import RETRIEVAL_ROUTE_EXCEPTION_MAPPING
from dependency_injector.wiring import Provide, inject
from fastapi import APIRouter, Depends, Query, status

router = APIRouter(prefix="/retrieval/search", tags=["search"])


@router.get(
    "",
    response_model=ItemSearchResponse,
    description="Legacy candidate search operation without full content.",
    status_code=status.HTTP_200_OK,
    summary="Search",
)
@router_exception_status(RETRIEVAL_ROUTE_EXCEPTION_MAPPING)
@inject
async def search(
    q: str = Query(min_length=1),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    item_search_service: ItemSearchService = Depends(
        Provide[ApplicationContainer.library.item_search_service]
    ),
) -> ItemSearchResponse:
    """Search all item types.

    Args:
        q [str]: Value supplied to search.
        limit [int]: Value supplied to search.
        offset [int]: Value supplied to search.
        item_search_service [ItemSearchService]: Value supplied to search.

    Returns:
        ItemSearchResponse: Value produced by search.
    """
    payload = await item_search_service.search(query=q, limit=limit, offset=offset)
    validation = ItemSearchResponse.model_validate(payload)
    return validation


@router.get(
    "/library/skills",
    response_model=ItemSearchResponse,
    description="Legacy skill candidate search operation without full content.",
    status_code=status.HTTP_200_OK,
    summary="Search skills",
)
@router_exception_status(RETRIEVAL_ROUTE_EXCEPTION_MAPPING)
@inject
async def search_skills(
    q: str = Query(min_length=1),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    item_search_service: ItemSearchService = Depends(
        Provide[ApplicationContainer.library.item_search_service]
    ),
) -> ItemSearchResponse:
    """Search only skill items.

    Args:
        q [str]: Value supplied to search_skills.
        limit [int]: Value supplied to search_skills.
        offset [int]: Value supplied to search_skills.
        item_search_service [ItemSearchService]: Value supplied to search_skills.

    Returns:
        ItemSearchResponse: Value produced by search_skills.
    """
    payload = await item_search_service.search(
        query=q,
        item_type=ItemType.SKILL,
        limit=limit,
        offset=offset,
    )
    validation = ItemSearchResponse.model_validate(payload)
    return validation


@router.get(
    "/library/knowledge",
    response_model=ItemSearchResponse,
    description="Legacy knowledge candidate search operation without full content.",
    status_code=status.HTTP_200_OK,
    summary="Search knowledge",
)
@router_exception_status(RETRIEVAL_ROUTE_EXCEPTION_MAPPING)
@inject
async def search_knowledge(
    q: str = Query(min_length=1),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    item_search_service: ItemSearchService = Depends(
        Provide[ApplicationContainer.library.item_search_service]
    ),
) -> ItemSearchResponse:
    """Search only knowledge items.

    Args:
        q [str]: Value supplied to search_knowledge.
        limit [int]: Value supplied to search_knowledge.
        offset [int]: Value supplied to search_knowledge.
        item_search_service [ItemSearchService]: Value supplied to search_knowledge.

    Returns:
        ItemSearchResponse: Value produced by search_knowledge.
    """
    payload = await item_search_service.search(
        query=q,
        item_type=ItemType.KNOWLEDGE,
        limit=limit,
        offset=offset,
    )
    validation = ItemSearchResponse.model_validate(payload)
    return validation
