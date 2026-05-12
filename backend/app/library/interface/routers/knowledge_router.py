"""Knowledge routes."""

from __future__ import annotations

from app.library.application.item_service import ItemService
from app.library.application.knowledge_service import KnowledgeService
from app.library.domain.entities.enums import ItemType
from app.library.interface.routers._helpers import (
    build_patch_payload,
    ensure_item_type,
)
from app.library.interface.routers.dependencies import (
    get_item_service,
    get_knowledge_service,
)
from app.library.interface.schemas.item_schema import ItemResponse
from app.library.interface.schemas.knowledge_schema import (
    KnowledgeCreateRequest,
    KnowledgePatchRequest,
)
from app.shared.exceptions import LibraryResourceNotFoundError
from fastapi import APIRouter, Depends, HTTPException, Query, status

router = APIRouter(prefix="/knowledge", tags=["knowledge"])


@router.post("", response_model=ItemResponse, status_code=status.HTTP_201_CREATED)
async def create_knowledge(
    request: KnowledgeCreateRequest,
    knowledge_service: KnowledgeService = Depends(get_knowledge_service),
) -> ItemResponse:
    """Create one knowledge item."""
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
    return ItemResponse.model_validate(payload)


@router.get("", response_model=list[ItemResponse])
async def list_knowledge(
    item_service: ItemService = Depends(get_item_service),
    limit: int = Query(default=100, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
) -> list[ItemResponse]:
    """List knowledge entries."""
    rows, _ = await item_service.list_items(
        item_type=ItemType.KNOWLEDGE,
        limit=limit,
        offset=offset,
    )
    return [ItemResponse.model_validate(row) for row in rows]


@router.get("/{item_id}", response_model=ItemResponse)
async def get_knowledge(
    item_id: int,
    item_service: ItemService = Depends(get_item_service),
) -> ItemResponse:
    """Get one knowledge entry."""
    try:
        payload = await item_service.get_item(item_id)
    except LibraryResourceNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    ensure_item_type(
        payload,
        expected=ItemType.KNOWLEDGE,
        detail="Not a knowledge item",
    )
    return ItemResponse.model_validate(payload)


@router.patch("/{item_id}", response_model=ItemResponse)
async def patch_knowledge(
    item_id: int,
    request: KnowledgePatchRequest,
    knowledge_service: KnowledgeService = Depends(get_knowledge_service),
) -> ItemResponse:
    """Patch one knowledge item."""
    patch_payload = build_patch_payload(request.model_dump())

    try:
        payload = await knowledge_service.patch_knowledge(
            item_id=item_id,
            payload=patch_payload,
        )
    except LibraryResourceNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    ensure_item_type(
        payload,
        expected=ItemType.KNOWLEDGE,
        detail="Not a knowledge item",
    )
    return ItemResponse.model_validate(payload)


@router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_knowledge(
    item_id: int,
    knowledge_service: KnowledgeService = Depends(get_knowledge_service),
) -> None:
    """Delete one knowledge item."""
    try:
        payload = await knowledge_service.item_service.get_item(item_id)
    except LibraryResourceNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    ensure_item_type(
        payload,
        expected=ItemType.KNOWLEDGE,
        detail="Not a knowledge item",
    )
    await knowledge_service.item_service.delete_item(item_id)
