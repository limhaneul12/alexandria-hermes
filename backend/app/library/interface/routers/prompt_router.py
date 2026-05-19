"""Prompt-specific routes."""

from __future__ import annotations

from typing import cast

from app.container import ApplicationContainer
from app.library.application.item_service import ItemService
from app.library.application.prompt_service import PromptService
from app.library.domain.event_enum.item_enums import CreatedByType, ItemType, SourceType
from app.library.domain.types.prompt_payload_types import PromptVariablePayload
from app.library.interface.routers._helpers import (
    build_patch_payload,
    ensure_item_type,
)
from app.library.interface.schemas.item.item_schema import (
    ItemResponse,
    ItemResponseList,
)
from app.library.interface.schemas.prompt.request_schemas import (
    AgentSubmitPromptRequest,
    PromptPatchRequest,
)
from app.shared.exceptions.exception_decorators import router_exception_status
from app.shared.exceptions.route_exceptions import LIBRARY_ROUTE_EXCEPTION_MAPPING
from dependency_injector.wiring import Provide, inject
from fastapi import APIRouter, Depends, Query, status

router = APIRouter(prefix="/library/prompts", tags=["prompts"])


@router.post(
    "/submit-by-agent",
    response_model=ItemResponse,
    status_code=status.HTTP_201_CREATED,
    description="Agent-authored prompt submission.",
    summary="Submit prompt by agent",
)
@router_exception_status(LIBRARY_ROUTE_EXCEPTION_MAPPING)
@inject
async def submit_prompt_by_agent(
    request: AgentSubmitPromptRequest,
    prompt_service: PromptService = Depends(
        Provide[ApplicationContainer.library.prompt_service]
    ),
) -> ItemResponse:
    """Persist an agent-authored prompt without exposing human prompt creation.

    Args:
        request: Agent prompt submission payload.
        prompt_service: Prompt service dependency.

    Returns:
        Created prompt item response.
    """
    payload = await prompt_service.create_prompt(
        title=request.title,
        summary=request.summary,
        content=request.content,
        category_id=request.category_id,
        tags=request.tags,
        content_format=request.content_format,
        prompt_kind=request.prompt_kind,
        prompt_domain=request.prompt_domain,
        prompt_task_type=request.prompt_task_type,
        input_variables=cast(
            list[PromptVariablePayload],
            [item.model_dump() for item in request.input_variables],
        ),
        output_format=request.output_format,
        target_actor=request.target_actor,
        target_model_family=request.target_model_family,
        language=request.language,
        related_item_ids=request.related_item_ids,
        safety_notes=request.safety_notes,
        version=request.version,
        change_summary=request.change_summary,
        created_by_name=request.created_by_name,
        created_by_type=CreatedByType.AGENT,
        source_type=SourceType.AGENT_SUBMITTED,
        status=request.status,
    )
    validation = ItemResponse.model_validate(payload)
    return validation


@router.get(
    "",
    response_model=ItemResponseList,
    description="Library API operation.",
    status_code=status.HTTP_200_OK,
    summary="List prompts",
)
@router_exception_status(LIBRARY_ROUTE_EXCEPTION_MAPPING)
@inject
async def list_prompts(
    item_service: ItemService = Depends(
        Provide[ApplicationContainer.library.item_service]
    ),
    limit: int = Query(default=100, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
) -> ItemResponseList:
    """List all prompt items.

    Args:
        item_service: Item service dependency.
        limit: Page size.
        offset: Page offset.

    Returns:
        Prompt item response list.
    """
    rows, _ = await item_service.list_items(
        item_type=ItemType.PROMPT,
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
    summary="Get prompt",
)
@router_exception_status(LIBRARY_ROUTE_EXCEPTION_MAPPING)
@inject
async def get_prompt(
    item_id: str,
    item_service: ItemService = Depends(
        Provide[ApplicationContainer.library.item_service]
    ),
) -> ItemResponse:
    """Get one prompt.

    Args:
        item_id: Target item id.
        item_service: Item service dependency.

    Returns:
        Prompt item response.
    """
    payload = await item_service.get_item(item_id)
    ensure_item_type(payload, expected=ItemType.PROMPT, detail="Not a prompt item")
    validation = ItemResponse.model_validate(payload)
    return validation


@router.patch(
    "/{item_id}",
    response_model=ItemResponse,
    description="Library API operation.",
    status_code=status.HTTP_200_OK,
    summary="Patch prompt",
)
@router_exception_status(LIBRARY_ROUTE_EXCEPTION_MAPPING)
@inject
async def patch_prompt(
    item_id: str,
    request: PromptPatchRequest,
    prompt_service: PromptService = Depends(
        Provide[ApplicationContainer.library.prompt_service]
    ),
) -> ItemResponse:
    """Patch one prompt item.

    Args:
        item_id: Target item id.
        request: Prompt patch request.
        prompt_service: Prompt service dependency.

    Returns:
        Patched item response.
    """
    patch_payload = build_patch_payload(request.model_dump())
    payload = await prompt_service.patch_prompt(
        item_id=item_id,
        payload=patch_payload,
    )
    ensure_item_type(payload, expected=ItemType.PROMPT, detail="Not a prompt item")
    validation = ItemResponse.model_validate(payload)
    return validation


@router.delete(
    "/{item_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    description="Library API operation.",
    summary="Delete prompt",
)
@router_exception_status(LIBRARY_ROUTE_EXCEPTION_MAPPING)
@inject
async def delete_prompt(
    item_id: str,
    prompt_service: PromptService = Depends(
        Provide[ApplicationContainer.library.prompt_service]
    ),
) -> None:
    """Delete one prompt item.

    Args:
        item_id: Target item id.
        prompt_service: Prompt service dependency.

    Returns:
        None.
    """
    item = await prompt_service.item_service.get_item(item_id)
    ensure_item_type(item, expected=ItemType.PROMPT, detail="Not a prompt item")
    await prompt_service.item_service.delete_item(item_id)
