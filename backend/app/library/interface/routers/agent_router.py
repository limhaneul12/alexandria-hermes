"""Agent profile routes."""

from __future__ import annotations

from app.container import ApplicationContainer
from app.library.application.agent_service import AgentService
from app.library.domain.entities.read_models import AgentProfile
from app.library.interface.schemas.agent.agent_schema import (
    AgentCreateRequest,
    AgentPatchRequest,
    AgentResponse,
    AgentResponseList,
)
from app.shared.exceptions.exception_decorators import router_exception_status
from app.shared.exceptions.route_exceptions import LIBRARY_ROUTE_EXCEPTION_MAPPING
from app.shared.types.types_convert_utils import now_utc
from dependency_injector.wiring import Provide, inject
from fastapi import APIRouter, Depends, HTTPException, status

router = APIRouter(prefix="/agents", tags=["agents"])


def _to_response(model: AgentProfile) -> AgentResponse:
    """Project ORM row to response model."""
    validation = AgentResponse.model_validate(model)
    return validation


@router.post(
    "",
    response_model=AgentResponse,
    status_code=status.HTTP_201_CREATED,
    description="Library API operation.",
    summary="Create agent",
)
@router_exception_status(LIBRARY_ROUTE_EXCEPTION_MAPPING)
@inject
async def create_agent(
    request: AgentCreateRequest,
    service: AgentService = Depends(
        Provide[ApplicationContainer.library.agent_service]
    ),
) -> AgentResponse:
    """Create an agent profile.

    Args:
        request [AgentCreateRequest]: Value supplied to create_agent.
        service [AgentService]: Value supplied to create_agent.

    Returns:
        AgentResponse: Value produced by create_agent.
    """
    now = now_utc()
    payload = request.model_dump()
    payload.update({"created_at": now, "updated_at": now})
    model = await service.create_agent(payload)
    return _to_response(model)


@router.get(
    "",
    response_model=AgentResponseList,
    description="Library API operation.",
    status_code=status.HTTP_200_OK,
    summary="List agents",
)
@router_exception_status(LIBRARY_ROUTE_EXCEPTION_MAPPING)
@inject
async def list_agents(
    service: AgentService = Depends(
        Provide[ApplicationContainer.library.agent_service]
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
@router_exception_status(LIBRARY_ROUTE_EXCEPTION_MAPPING)
@inject
async def get_agent(
    agent_id: str,
    service: AgentService = Depends(
        Provide[ApplicationContainer.library.agent_service]
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
@router_exception_status(LIBRARY_ROUTE_EXCEPTION_MAPPING)
@inject
async def patch_agent(
    agent_id: str,
    request: AgentPatchRequest,
    service: AgentService = Depends(
        Provide[ApplicationContainer.library.agent_service]
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
    payload = request.model_dump(exclude_unset=True)
    payload["updated_at"] = now_utc()
    model = await service.update_agent(agent_id, payload)
    return _to_response(model)


@router.delete(
    "/{agent_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    description="Library API operation.",
    summary="Delete agent",
)
@router_exception_status(LIBRARY_ROUTE_EXCEPTION_MAPPING)
@inject
async def delete_agent(
    agent_id: str,
    service: AgentService = Depends(
        Provide[ApplicationContainer.library.agent_service]
    ),
) -> None:
    """Delete one profile.

    Args:
        agent_id [str]: Value supplied to delete_agent.
        service [AgentService]: Value supplied to delete_agent.
    """
    await service.delete_agent(agent_id)
