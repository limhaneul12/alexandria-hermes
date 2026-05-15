"""Workflow routes."""

from __future__ import annotations

from app.container import ApplicationContainer
from app.library.application.item_service import ItemService
from app.library.application.workflow_service import WorkflowService
from app.library.domain.event_enum.item_enums import ItemType
from app.library.interface.routers._helpers import (
    build_patch_payload,
    ensure_item_type,
)
from app.library.interface.schemas.item.item_schema import (
    ItemResponse,
    ItemResponseList,
)
from app.library.interface.schemas.workflow.workflow_schema import (
    WorkflowCreateRequest,
    WorkflowPatchRequest,
)
from app.shared.exceptions.exception_decorators import router_exception_status
from app.shared.exceptions.route_exceptions import LIBRARY_ROUTE_EXCEPTION_MAPPING
from dependency_injector.wiring import Provide, inject
from fastapi import APIRouter, Depends, Query, status

router = APIRouter(prefix="/library/workflows", tags=["workflows"])


@router.post(
    "",
    response_model=ItemResponse,
    status_code=status.HTTP_201_CREATED,
    description="Library API operation.",
    summary="Create workflow",
)
@router_exception_status(LIBRARY_ROUTE_EXCEPTION_MAPPING)
@inject
async def create_workflow(
    request: WorkflowCreateRequest,
    workflow_service: WorkflowService = Depends(
        Provide[ApplicationContainer.library.workflow_service]
    ),
) -> ItemResponse:
    """Create one workflow.

    Args:
        request [WorkflowCreateRequest]: Value supplied to create_workflow.
        workflow_service [WorkflowService]: Value supplied to create_workflow.

    Returns:
        ItemResponse: Value produced by create_workflow.
    """
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
    validation = ItemResponse.model_validate(payload)
    return validation


@router.get(
    "",
    response_model=ItemResponseList,
    description="Library API operation.",
    status_code=status.HTTP_200_OK,
    summary="List workflows",
)
@router_exception_status(LIBRARY_ROUTE_EXCEPTION_MAPPING)
@inject
async def list_workflows(
    item_service: ItemService = Depends(
        Provide[ApplicationContainer.library.item_service]
    ),
    limit: int = Query(default=100, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
) -> ItemResponseList:
    """List workflows.

    Args:
        item_service [ItemService]: Value supplied to list_workflows.
        limit [int]: Value supplied to list_workflows.
        offset [int]: Value supplied to list_workflows.

    Returns:
        ItemResponseList: Value produced by list_workflows.
    """
    rows, _ = await item_service.list_items(
        item_type=ItemType.WORKFLOW,
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
    summary="Get workflow",
)
@router_exception_status(LIBRARY_ROUTE_EXCEPTION_MAPPING)
@inject
async def get_workflow(
    item_id: str,
    item_service: ItemService = Depends(
        Provide[ApplicationContainer.library.item_service]
    ),
) -> ItemResponse:
    """Get one workflow.

    Args:
        item_id [str]: Value supplied to get_workflow.
        item_service [ItemService]: Value supplied to get_workflow.

    Returns:
        ItemResponse: Value produced by get_workflow.
    """
    payload = await item_service.get_item(item_id)
    ensure_item_type(
        payload,
        expected=ItemType.WORKFLOW,
        detail="Not a workflow item",
    )
    validation = ItemResponse.model_validate(payload)
    return validation


@router.patch(
    "/{item_id}",
    response_model=ItemResponse,
    description="Library API operation.",
    status_code=status.HTTP_200_OK,
    summary="Patch workflow",
)
@router_exception_status(LIBRARY_ROUTE_EXCEPTION_MAPPING)
@inject
async def patch_workflow(
    item_id: str,
    request: WorkflowPatchRequest,
    workflow_service: WorkflowService = Depends(
        Provide[ApplicationContainer.library.workflow_service]
    ),
) -> ItemResponse:
    """Patch workflow item fields.

    Args:
        item_id [str]: Value supplied to patch_workflow.
        request [WorkflowPatchRequest]: Value supplied to patch_workflow.
        workflow_service [WorkflowService]: Value supplied to patch_workflow.

    Returns:
        ItemResponse: Value produced by patch_workflow.
    """
    patch_payload = build_patch_payload(request.model_dump())

    payload = await workflow_service.patch_workflow(
        item_id=item_id,
        payload=patch_payload,
    )
    ensure_item_type(
        payload,
        expected=ItemType.WORKFLOW,
        detail="Not a workflow item",
    )
    validation = ItemResponse.model_validate(payload)
    return validation


@router.delete(
    "/{item_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    description="Library API operation.",
    summary="Delete workflow",
)
@router_exception_status(LIBRARY_ROUTE_EXCEPTION_MAPPING)
@inject
async def delete_workflow(
    item_id: str,
    workflow_service: WorkflowService = Depends(
        Provide[ApplicationContainer.library.workflow_service]
    ),
) -> None:
    """Delete one workflow.

    Args:
        item_id [str]: Value supplied to delete_workflow.
        workflow_service [WorkflowService]: Value supplied to delete_workflow.
    """
    payload = await workflow_service.item_service.get_item(item_id)
    ensure_item_type(
        payload,
        expected=ItemType.WORKFLOW,
        detail="Not a workflow item",
    )
    await workflow_service.item_service.delete_item(item_id)
