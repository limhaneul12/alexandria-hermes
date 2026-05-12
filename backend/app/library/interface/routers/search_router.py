"""Search routes backed by SQLite FTS5."""

from __future__ import annotations

from app.library.application.item_service import ItemService
from app.library.domain.entities.enums import ItemType
from app.library.interface.routers.dependencies import get_item_service
from app.library.interface.schemas.item_schema import ItemResponse
from fastapi import APIRouter, Depends, Query

router = APIRouter(prefix="/search", tags=["search"])


@router.get("", response_model=list[ItemResponse])
async def search(
    q: str = Query(min_length=1),
    item_service: ItemService = Depends(get_item_service),
) -> list[ItemResponse]:
    """Search all item types."""
    items = await item_service.search(query=q)
    return [ItemResponse.model_validate(item) for item in items]


@router.get("/skills", response_model=list[ItemResponse])
async def search_skills(
    q: str = Query(min_length=1),
    item_service: ItemService = Depends(get_item_service),
) -> list[ItemResponse]:
    """Search only skill items."""
    items = await item_service.search(query=q, item_type=ItemType.SKILL)
    return [ItemResponse.model_validate(item) for item in items]


@router.get("/workflows", response_model=list[ItemResponse])
async def search_workflows(
    q: str = Query(min_length=1),
    item_service: ItemService = Depends(get_item_service),
) -> list[ItemResponse]:
    """Search only workflow items."""
    items = await item_service.search(query=q, item_type=ItemType.WORKFLOW)
    return [ItemResponse.model_validate(item) for item in items]


@router.get("/knowledge", response_model=list[ItemResponse])
async def search_knowledge(
    q: str = Query(min_length=1),
    item_service: ItemService = Depends(get_item_service),
) -> list[ItemResponse]:
    """Search only knowledge items."""
    items = await item_service.search(query=q, item_type=ItemType.KNOWLEDGE)
    return [ItemResponse.model_validate(item) for item in items]
