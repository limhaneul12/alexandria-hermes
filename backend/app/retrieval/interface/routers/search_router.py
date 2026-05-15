"""Search routes backed by SQLite FTS5."""

from __future__ import annotations

from app.container import ApplicationContainer
from app.library.application.item_service import ItemService
from app.library.domain.event_enum.item_enums import ItemType
from app.library.interface.schemas.item.item_schema import ItemResponseList
from app.shared.exceptions.exception_decorators import router_exception_status
from app.shared.exceptions.route_exceptions import LIBRARY_ROUTE_EXCEPTION_MAPPING
from dependency_injector.wiring import Provide, inject
from fastapi import APIRouter, Depends, Query, status

router = APIRouter(prefix="/retrieval/search", tags=["search"])


@router.get(
    "",
    response_model=ItemResponseList,
    description="Library API operation.",
    status_code=status.HTTP_200_OK,
    summary="Search",
)
@router_exception_status(LIBRARY_ROUTE_EXCEPTION_MAPPING)
@inject
async def search(
    q: str = Query(min_length=1),
    item_service: ItemService = Depends(
        Provide[ApplicationContainer.library.item_service]
    ),
) -> ItemResponseList:
    """Search all item types.

    Args:
        q [str]: Value supplied to search.
        item_service [ItemService]: Value supplied to search.

    Returns:
        ItemResponseList: Value produced by search.
    """
    items = await item_service.search(query=q)
    validation = ItemResponseList.model_validate(items)
    return validation


@router.get(
    "/library/skills",
    response_model=ItemResponseList,
    description="Library API operation.",
    status_code=status.HTTP_200_OK,
    summary="Search skills",
)
@router_exception_status(LIBRARY_ROUTE_EXCEPTION_MAPPING)
@inject
async def search_skills(
    q: str = Query(min_length=1),
    item_service: ItemService = Depends(
        Provide[ApplicationContainer.library.item_service]
    ),
) -> ItemResponseList:
    """Search only skill items.

    Args:
        q [str]: Value supplied to search_skills.
        item_service [ItemService]: Value supplied to search_skills.

    Returns:
        ItemResponseList: Value produced by search_skills.
    """
    items = await item_service.search(query=q, item_type=ItemType.SKILL)
    validation = ItemResponseList.model_validate(items)
    return validation


@router.get(
    "/library/workflows",
    response_model=ItemResponseList,
    description="Library API operation.",
    status_code=status.HTTP_200_OK,
    summary="Search workflows",
)
@router_exception_status(LIBRARY_ROUTE_EXCEPTION_MAPPING)
@inject
async def search_workflows(
    q: str = Query(min_length=1),
    item_service: ItemService = Depends(
        Provide[ApplicationContainer.library.item_service]
    ),
) -> ItemResponseList:
    """Search only workflow items.

    Args:
        q [str]: Value supplied to search_workflows.
        item_service [ItemService]: Value supplied to search_workflows.

    Returns:
        ItemResponseList: Value produced by search_workflows.
    """
    items = await item_service.search(query=q, item_type=ItemType.WORKFLOW)
    validation = ItemResponseList.model_validate(items)
    return validation


@router.get(
    "/library/knowledge",
    response_model=ItemResponseList,
    description="Library API operation.",
    status_code=status.HTTP_200_OK,
    summary="Search knowledge",
)
@router_exception_status(LIBRARY_ROUTE_EXCEPTION_MAPPING)
@inject
async def search_knowledge(
    q: str = Query(min_length=1),
    item_service: ItemService = Depends(
        Provide[ApplicationContainer.library.item_service]
    ),
) -> ItemResponseList:
    """Search only knowledge items.

    Args:
        q [str]: Value supplied to search_knowledge.
        item_service [ItemService]: Value supplied to search_knowledge.

    Returns:
        ItemResponseList: Value produced by search_knowledge.
    """
    items = await item_service.search(query=q, item_type=ItemType.KNOWLEDGE)
    validation = ItemResponseList.model_validate(items)
    return validation
