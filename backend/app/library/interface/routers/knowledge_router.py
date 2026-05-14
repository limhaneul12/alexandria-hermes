"""Knowledge routes."""

from __future__ import annotations

from app.container import ApplicationContainer
from app.library.application.item_service import ItemService
from app.library.application.knowledge_service import KnowledgeService
from app.library.domain.event_enum.item_enums import ItemType
from app.library.interface.routers._helpers import (
    build_patch_payload,
    ensure_item_type,
)
from app.library.interface.schemas.item.item_schema import (
    ItemResponse,
    ItemResponseList,
)
from app.library.interface.schemas.knowledge.knowledge_schema import (
    KnowledgeCreateRequest,
    KnowledgePatchRequest,
)
from app.shared.exceptions.exception_decorators import router_exception_status
from app.shared.exceptions.route_exceptions import LIBRARY_ROUTE_EXCEPTION_MAPPING
from dependency_injector.wiring import Provide, inject
from fastapi import APIRouter, Depends, Query, status

router = APIRouter(prefix="/knowledge", tags=["knowledge"])


@router.post(
    "",
    response_model=ItemResponse,
    status_code=status.HTTP_201_CREATED,
    description="Library API operation.",
    summary="Create knowledge",
)
@router_exception_status(LIBRARY_ROUTE_EXCEPTION_MAPPING)
@inject
async def create_knowledge(
    request: KnowledgeCreateRequest,
    knowledge_service: KnowledgeService = Depends(
        Provide[ApplicationContainer.library.knowledge_service]
    ),
) -> ItemResponse:
    """Create one knowledge item.

    Args:
        request [KnowledgeCreateRequest]: Value supplied to create_knowledge.
        knowledge_service [KnowledgeService]: Value supplied to create_knowledge.

    Returns:
        ItemResponse: Value produced by create_knowledge.
    """
    payload = await knowledge_service.create_knowledge(
        title=request.title,
        summary=request.summary,
        content=request.content,
        category_id=request.category_id,
        tags=request.tags,
        body=request.body,
        references=request.references,
        related_items=request.related_items,
        created_by_name=request.created_by_name,
        status=request.status,
    )
    validation = ItemResponse.model_validate(payload)
    return validation


@router.get(
    "",
    response_model=ItemResponseList,
    description="Library API operation.",
    status_code=status.HTTP_200_OK,
    summary="List knowledge",
)
@router_exception_status(LIBRARY_ROUTE_EXCEPTION_MAPPING)
@inject
async def list_knowledge(
    item_service: ItemService = Depends(
        Provide[ApplicationContainer.library.item_service]
    ),
    limit: int = Query(default=100, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
) -> ItemResponseList:
    """List knowledge entries.

    Args:
        item_service [ItemService]: Value supplied to list_knowledge.
        limit [int]: Value supplied to list_knowledge.
        offset [int]: Value supplied to list_knowledge.

    Returns:
        ItemResponseList: Value produced by list_knowledge.
    """
    rows, _ = await item_service.list_items(
        item_type=ItemType.KNOWLEDGE,
        limit=limit,
        offset=offset,
    )
    validation = ItemResponseList.model_validate(rows)
    return validation


@router.get(
    "/{item_id}",
    response_model=ItemResponse,
    description="Library API operation.",
    status_code=status.HTTP_200_OK,
    summary="Get knowledge",
)
@router_exception_status(LIBRARY_ROUTE_EXCEPTION_MAPPING)
@inject
async def get_knowledge(
    item_id: str,
    item_service: ItemService = Depends(
        Provide[ApplicationContainer.library.item_service]
    ),
) -> ItemResponse:
    """Get one knowledge entry.

    Args:
        item_id [str]: Value supplied to get_knowledge.
        item_service [ItemService]: Value supplied to get_knowledge.

    Returns:
        ItemResponse: Value produced by get_knowledge.
    """
    payload = await item_service.get_item(item_id)
    ensure_item_type(
        payload,
        expected=ItemType.KNOWLEDGE,
        detail="Not a knowledge item",
    )
    validation = ItemResponse.model_validate(payload)
    return validation


@router.patch(
    "/{item_id}",
    response_model=ItemResponse,
    description="Library API operation.",
    status_code=status.HTTP_200_OK,
    summary="Patch knowledge",
)
@router_exception_status(LIBRARY_ROUTE_EXCEPTION_MAPPING)
@inject
async def patch_knowledge(
    item_id: str,
    request: KnowledgePatchRequest,
    knowledge_service: KnowledgeService = Depends(
        Provide[ApplicationContainer.library.knowledge_service]
    ),
) -> ItemResponse:
    """Patch one knowledge item.

    Args:
        item_id [str]: Value supplied to patch_knowledge.
        request [KnowledgePatchRequest]: Value supplied to patch_knowledge.
        knowledge_service [KnowledgeService]: Value supplied to patch_knowledge.

    Returns:
        ItemResponse: Value produced by patch_knowledge.
    """
    patch_payload = build_patch_payload(request.model_dump())

    payload = await knowledge_service.patch_knowledge(
        item_id=item_id,
        payload=patch_payload,
    )
    ensure_item_type(
        payload,
        expected=ItemType.KNOWLEDGE,
        detail="Not a knowledge item",
    )
    validation = ItemResponse.model_validate(payload)
    return validation


@router.delete(
    "/{item_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    description="Library API operation.",
    summary="Delete knowledge",
)
@router_exception_status(LIBRARY_ROUTE_EXCEPTION_MAPPING)
@inject
async def delete_knowledge(
    item_id: str,
    knowledge_service: KnowledgeService = Depends(
        Provide[ApplicationContainer.library.knowledge_service]
    ),
) -> None:
    """Delete one knowledge item.

    Args:
        item_id [str]: Value supplied to delete_knowledge.
        knowledge_service [KnowledgeService]: Value supplied to delete_knowledge.
    """
    payload = await knowledge_service.item_service.get_item(item_id)
    ensure_item_type(
        payload,
        expected=ItemType.KNOWLEDGE,
        detail="Not a knowledge item",
    )
    await knowledge_service.item_service.delete_item(item_id)
