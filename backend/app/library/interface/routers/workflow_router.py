"""Workflow routes."""

from __future__ import annotations

from app.library.application.item_service import ItemService
from app.library.application.workflow_service import WorkflowService
from app.library.domain.entities.enums import ItemType
from app.library.interface.routers._helpers import (
    build_patch_payload,
    ensure_item_type,
)
from app.library.interface.routers.dependencies import (
    get_item_service,
    get_workflow_service,
)
from app.library.interface.schemas.item_schema import ItemResponse
from app.library.interface.schemas.workflow_schema import (
    WorkflowCreateRequest,
    WorkflowPatchRequest,
)
from app.shared.exceptions import LibraryResourceNotFoundError
from fastapi import APIRouter, Depends, HTTPException, Query, status

router = APIRouter(prefix="/workflows", tags=["workflows"])


@router.post("", response_model=ItemResponse, status_code=status.HTTP_201_CREATED)
async def create_workflow(
    request: WorkflowCreateRequest,
    workflow_service: WorkflowService = Depends(get_workflow_service),
) -> ItemResponse:
    """Create one workflow."""
    payload = await workflow_service.create_workflow(
        title=request.title,
        summary=request.summary,
        content=request.content,
        category_id=request.category_id,
        tags=request.tags,
        steps=request.steps,
        related_skill_ids=request.related_skill_ids,
        expected_result=request.expected_result,
        use_case=request.use_case,
        created_by_name=request.created_by_name,
        status=request.status,
    )
    return ItemResponse.model_validate(payload)


@router.get("", response_model=list[ItemResponse])
async def list_workflows(
    item_service: ItemService = Depends(get_item_service),
    limit: int = Query(default=100, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
) -> list[ItemResponse]:
    """List workflows."""
    rows, _ = await item_service.list_items(
        item_type=ItemType.WORKFLOW,
        limit=limit,
        offset=offset,
    )
    return [ItemResponse.model_validate(row) for row in rows]


@router.get("/{item_id}", response_model=ItemResponse)
async def get_workflow(
    item_id: int,
    item_service: ItemService = Depends(get_item_service),
) -> ItemResponse:
    """Get one workflow."""
    try:
        payload = await item_service.get_item(item_id)
    except LibraryResourceNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    ensure_item_type(
        payload,
        expected=ItemType.WORKFLOW,
        detail="Not a workflow item",
    )
    return ItemResponse.model_validate(payload)


@router.patch("/{item_id}", response_model=ItemResponse)
async def patch_workflow(
    item_id: int,
    request: WorkflowPatchRequest,
    workflow_service: WorkflowService = Depends(get_workflow_service),
) -> ItemResponse:
    """Patch workflow item fields."""
    patch_payload = build_patch_payload(request.model_dump())

    try:
        payload = await workflow_service.patch_workflow(
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
        expected=ItemType.WORKFLOW,
        detail="Not a workflow item",
    )
    return ItemResponse.model_validate(payload)


@router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_workflow(
    item_id: int,
    workflow_service: WorkflowService = Depends(get_workflow_service),
) -> None:
    """Delete one workflow."""
    try:
        payload = await workflow_service.item_service.get_item(item_id)
    except LibraryResourceNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    ensure_item_type(
        payload,
        expected=ItemType.WORKFLOW,
        detail="Not a workflow item",
    )
    await workflow_service.item_service.delete_item(item_id)
