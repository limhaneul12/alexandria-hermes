"""Skill-specific routes."""

from __future__ import annotations

from typing import cast

from app.container import ApplicationContainer
from app.library.application.item_service import ItemService
from app.library.application.skill_service import SkillService
from app.library.domain.event_enum.item_enums import ItemStatus, ItemType
from app.library.domain.types.skill_payload_types import SkillSchemaPayload
from app.library.interface.routers._helpers import (
    build_patch_payload,
    ensure_item_type,
)
from app.library.interface.schemas.item.item_schema import (
    ItemResponse,
    ItemResponseList,
)
from app.library.interface.schemas.skill.request_schemas import (
    AgentSubmitSkillRequest,
    SkillCreateRequest,
    SkillPatchRequest,
)
from app.shared.exceptions.exception_decorators import router_exception_status
from app.shared.exceptions.route_exceptions import LIBRARY_ROUTE_EXCEPTION_MAPPING
from app.shared.types.types_convert_utils import enum_value
from dependency_injector.wiring import Provide, inject
from fastapi import APIRouter, Depends, Query, status

router = APIRouter(prefix="/library/skills", tags=["skills"])


@router.post(
    "",
    response_model=ItemResponse,
    status_code=status.HTTP_201_CREATED,
    description="Library API operation.",
    summary="Create skill",
)
@router_exception_status(LIBRARY_ROUTE_EXCEPTION_MAPPING)
@inject
async def create_skill(
    request: SkillCreateRequest,
    skill_service: SkillService = Depends(
        Provide[ApplicationContainer.library.skill_service]
    ),
) -> ItemResponse:
    """Create one skill entry from manual input.

    Args:
        request [SkillCreateRequest]: Value supplied to create_skill.
        skill_service [SkillService]: Value supplied to create_skill.

    Returns:
        ItemResponse: Value produced by create_skill.
    """
    payload = await skill_service.create_skill(
        title=request.title,
        summary=request.summary,
        content=request.content,
        category_id=request.category_id,
        tags=request.tags,
        purpose=request.purpose,
        input_schema=cast(SkillSchemaPayload, request.input_schema),
        output_schema=cast(SkillSchemaPayload, request.output_schema),
        usage_example=request.usage_example,
        required_tools=request.required_tools,
        risk_level=request.risk_level,
        version=request.version,
        created_by_name=request.created_by_name,
        activate=enum_value(request.status, ItemStatus, "status") is ItemStatus.ACTIVE,
        status=request.status,
    )
    validation = ItemResponse.model_validate(payload)
    return validation


@router.post(
    "/submit-by-agent",
    response_model=ItemResponse,
    status_code=status.HTTP_201_CREATED,
    description="Library API operation.",
    summary="Submit skill by agent",
)
@router_exception_status(LIBRARY_ROUTE_EXCEPTION_MAPPING)
@inject
async def submit_skill_by_agent(
    request: AgentSubmitSkillRequest,
    skill_service: SkillService = Depends(
        Provide[ApplicationContainer.library.skill_service]
    ),
) -> ItemResponse:
    """Register structured skill payload from an external agent.

    Args:
        request [AgentSubmitSkillRequest]: Value supplied to submit_skill_by_agent.
        skill_service [SkillService]: Value supplied to submit_skill_by_agent.

    Returns:
        ItemResponse: Value produced by submit_skill_by_agent.
    """
    payload = await skill_service.create_skill_by_agent(
        title=request.title,
        content=request.content,
        summary=request.summary,
        category_id=request.category_id,
        tags=request.tags,
        purpose=request.purpose,
        input_schema=cast(SkillSchemaPayload, request.input_schema),
        output_schema=cast(SkillSchemaPayload, request.output_schema),
        usage_example=request.usage_example,
        required_tools=request.required_tools,
        risk_level=request.risk_level,
        version=request.version,
        created_by_name=request.created_by_name,
        activate=request.activate,
        status=request.status,
        evidence_urls=request.evidence_urls,
        source_summary=request.source_summary,
    )
    validation = ItemResponse.model_validate(payload)
    return validation


@router.get(
    "",
    response_model=ItemResponseList,
    description="Library API operation.",
    status_code=status.HTTP_200_OK,
    summary="List skills",
)
@router_exception_status(LIBRARY_ROUTE_EXCEPTION_MAPPING)
@inject
async def list_skills(
    item_service: ItemService = Depends(
        Provide[ApplicationContainer.library.item_service]
    ),
    limit: int = Query(default=100, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
) -> ItemResponseList:
    """List all skill items.

    Args:
        item_service [ItemService]: Value supplied to list_skills.
        limit [int]: Value supplied to list_skills.
        offset [int]: Value supplied to list_skills.

    Returns:
        ItemResponseList: Value produced by list_skills.
    """
    rows, _ = await item_service.list_items(
        item_type=ItemType.SKILL,
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
    summary="Get skill",
)
@router_exception_status(LIBRARY_ROUTE_EXCEPTION_MAPPING)
@inject
async def get_skill(
    item_id: str,
    item_service: ItemService = Depends(
        Provide[ApplicationContainer.library.item_service]
    ),
) -> ItemResponse:
    """Get one skill.

    Args:
        item_id [str]: Value supplied to get_skill.
        item_service [ItemService]: Value supplied to get_skill.

    Returns:
        ItemResponse: Value produced by get_skill.
    """
    payload = await item_service.get_item(item_id)
    ensure_item_type(
        payload,
        expected=ItemType.SKILL,
        detail="Not a skill item",
    )
    validation = ItemResponse.model_validate(payload)
    return validation


@router.patch(
    "/{item_id}",
    response_model=ItemResponse,
    description="Library API operation.",
    status_code=status.HTTP_200_OK,
    summary="Patch skill",
)
@router_exception_status(LIBRARY_ROUTE_EXCEPTION_MAPPING)
@inject
async def patch_skill(
    item_id: str,
    request: SkillPatchRequest,
    skill_service: SkillService = Depends(
        Provide[ApplicationContainer.library.skill_service]
    ),
) -> ItemResponse:
    """Patch one skill item.

    Args:
        item_id [str]: Value supplied to patch_skill.
        request [SkillPatchRequest]: Value supplied to patch_skill.
        skill_service [SkillService]: Value supplied to patch_skill.

    Returns:
        ItemResponse: Value produced by patch_skill.
    """
    patch_payload = build_patch_payload(request.model_dump())

    payload = await skill_service.patch_skill(
        item_id=item_id,
        payload=patch_payload,
    )
    ensure_item_type(
        payload,
        expected=ItemType.SKILL,
        detail="Not a skill item",
    )
    validation = ItemResponse.model_validate(payload)
    return validation


@router.delete(
    "/{item_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    description="Library API operation.",
    summary="Delete skill",
)
@router_exception_status(LIBRARY_ROUTE_EXCEPTION_MAPPING)
@inject
async def delete_skill(
    item_id: str,
    skill_service: SkillService = Depends(
        Provide[ApplicationContainer.library.skill_service]
    ),
) -> None:
    """Delete one skill item.

    Args:
        item_id [str]: Value supplied to delete_skill.
        skill_service [SkillService]: Value supplied to delete_skill.
    """
    item = await skill_service.item_service.get_item(item_id)
    ensure_item_type(
        item,
        expected=ItemType.SKILL,
        detail="Not a skill item",
    )
    await skill_service.item_service.delete_item(item_id)
