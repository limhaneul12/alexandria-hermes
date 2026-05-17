"""Agent profile routes."""

from __future__ import annotations

from app.container import ApplicationContainer
from app.librarian.application.agent_service import AgentService
from app.librarian.domain.entities.read_models import AgentProfile
from app.librarian.domain.types.agent_payload_types import (
    AgentCreatePayload,
    AgentUpdatePayload,
)
from app.librarian.interface.schemas.agent.agent_schema import (
    AgentCreateRequest,
    AgentPatchRequest,
    AgentResponse,
    AgentResponseList,
)
from app.platform.security.operator_api_key import require_operator_api_key
from app.shared.exceptions.exception_decorators import router_exception_status
from app.shared.exceptions.route_exceptions import LIBRARIAN_ROUTE_EXCEPTION_MAPPING
from app.shared.types.types_convert_utils import now_utc
from dependency_injector.wiring import Provide, inject
from fastapi import APIRouter, Depends, HTTPException, status

router = APIRouter(
    prefix="/librarians/profiles",
    tags=["agents"],
    dependencies=[Depends(require_operator_api_key)],
)


def _to_response(model: AgentProfile) -> AgentResponse:
    """Project ORM row to response model.

    Args:
        model: Agent profile read model.

    Returns:
        AgentResponse: Public agent response schema.
    """
    validation = AgentResponse.model_validate(model)
    return validation


def _create_payload(request: AgentCreateRequest) -> AgentCreatePayload:
    """Convert a create request into an application payload.

    Args:
        request: Validated create request.

    Returns:
        AgentCreatePayload: Application create payload.
    """
    now = now_utc()
    return AgentCreatePayload(
        name=request.name,
        provider=request.provider,
        description=request.description,
        capabilities=request.capabilities,
        preferred_librarian_provider=request.preferred_librarian_provider,
        preferred_librarian_model=request.preferred_librarian_model,
        max_librarian_agents=request.max_librarian_agents,
        librarian_role_prompt=request.librarian_role_prompt,
        librarian_role=request.librarian_role,
        librarian_specialties=request.librarian_specialties,
        librarian_routing_priority=request.librarian_routing_priority,
        librarian_enabled=request.librarian_enabled,
        created_at=now,
        updated_at=now,
    )


def _patch_payload(request: AgentPatchRequest) -> AgentUpdatePayload:
    """Convert a patch request into an application payload.

    Args:
        request: Validated patch request.

    Returns:
        AgentUpdatePayload: Explicit application patch payload.
    """
    fields = request.model_fields_set
    payload = AgentUpdatePayload()
    if "name" in fields and request.name is not None:
        payload["name"] = request.name
    if "provider" in fields and request.provider is not None:
        payload["provider"] = request.provider
    if "description" in fields:
        payload["description"] = request.description
    if "capabilities" in fields and request.capabilities is not None:
        payload["capabilities"] = request.capabilities
    if "preferred_librarian_provider" in fields:
        payload["preferred_librarian_provider"] = request.preferred_librarian_provider
    if "preferred_librarian_model" in fields:
        payload["preferred_librarian_model"] = request.preferred_librarian_model
    if "max_librarian_agents" in fields and request.max_librarian_agents is not None:
        payload["max_librarian_agents"] = request.max_librarian_agents
    if "librarian_role_prompt" in fields:
        payload["librarian_role_prompt"] = request.librarian_role_prompt
    if "librarian_role" in fields and request.librarian_role is not None:
        payload["librarian_role"] = request.librarian_role
    if "librarian_specialties" in fields and request.librarian_specialties is not None:
        payload["librarian_specialties"] = request.librarian_specialties
    if (
        "librarian_routing_priority" in fields
        and request.librarian_routing_priority is not None
    ):
        payload["librarian_routing_priority"] = request.librarian_routing_priority
    if "librarian_enabled" in fields and request.librarian_enabled is not None:
        payload["librarian_enabled"] = request.librarian_enabled
    return payload


@router.post(
    "",
    response_model=AgentResponse,
    status_code=status.HTTP_201_CREATED,
    description="Library API operation.",
    summary="Create agent",
)
@router_exception_status(LIBRARIAN_ROUTE_EXCEPTION_MAPPING)
@inject
async def create_agent(
    request: AgentCreateRequest,
    service: AgentService = Depends(
        Provide[ApplicationContainer.librarian.agent_service]
    ),
) -> AgentResponse:
    """Create an agent profile.

    Args:
        request [AgentCreateRequest]: Value supplied to create_agent.
        service [AgentService]: Value supplied to create_agent.

    Returns:
        AgentResponse: Value produced by create_agent.
    """
    model = await service.create_agent(_create_payload(request))
    return _to_response(model)


@router.get(
    "",
    response_model=AgentResponseList,
    description="Library API operation.",
    status_code=status.HTTP_200_OK,
    summary="List agents",
)
@router_exception_status(LIBRARIAN_ROUTE_EXCEPTION_MAPPING)
@inject
async def list_agents(
    service: AgentService = Depends(
        Provide[ApplicationContainer.librarian.agent_service]
    ),
) -> AgentResponseList:
    """List all agent profiles.

    Args:
        service [AgentService]: Value supplied to list_agents.

    Returns:
        AgentResponseList: Value produced by list_agents.
    """
    rows = await service.list_agents()
    validation = AgentResponseList.model_validate(rows)
    return validation


@router.get(
    "/{agent_id}",
    response_model=AgentResponse,
    description="Library API operation.",
    status_code=status.HTTP_200_OK,
    summary="Get agent",
)
@router_exception_status(LIBRARIAN_ROUTE_EXCEPTION_MAPPING)
@inject
async def get_agent(
    agent_id: str,
    service: AgentService = Depends(
        Provide[ApplicationContainer.librarian.agent_service]
    ),
) -> AgentResponse:
    """Get one profile.

    Args:
        agent_id [str]: Value supplied to get_agent.
        service [AgentService]: Value supplied to get_agent.

    Returns:
        AgentResponse: Value produced by get_agent.
    """
    model = await service.get_agent(agent_id)
    if model is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found"
        )
    return _to_response(model)


@router.patch(
    "/{agent_id}",
    response_model=AgentResponse,
    description="Library API operation.",
    status_code=status.HTTP_200_OK,
    summary="Patch agent",
)
@router_exception_status(LIBRARIAN_ROUTE_EXCEPTION_MAPPING)
@inject
async def patch_agent(
    agent_id: str,
    request: AgentPatchRequest,
    service: AgentService = Depends(
        Provide[ApplicationContainer.librarian.agent_service]
    ),
) -> AgentResponse:
    """Patch one profile.

    Args:
        agent_id [str]: Value supplied to patch_agent.
        request [AgentPatchRequest]: Value supplied to patch_agent.
        service [AgentService]: Value supplied to patch_agent.

    Returns:
        AgentResponse: Value produced by patch_agent.
    """
    model = await service.update_agent(agent_id, _patch_payload(request))
    return _to_response(model)


@router.delete(
    "/{agent_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    description="Library API operation.",
    summary="Delete agent",
)
@router_exception_status(LIBRARIAN_ROUTE_EXCEPTION_MAPPING)
@inject
async def delete_agent(
    agent_id: str,
    service: AgentService = Depends(
        Provide[ApplicationContainer.librarian.agent_service]
    ),
) -> None:
    """Delete one profile.

    Args:
        agent_id [str]: Value supplied to delete_agent.
        service [AgentService]: Value supplied to delete_agent.
    """
    await service.delete_agent(agent_id)
