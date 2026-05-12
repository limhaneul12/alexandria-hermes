"""Agent profile routes."""

from __future__ import annotations

from app.library.application.agent_service import AgentService
from app.library.application.common import now_utc
from app.library.domain.entities.read_models import AgentProfile
from app.library.interface.routers.dependencies import get_agent_service
from app.library.interface.schemas.agent_schema import (
    AgentCreateRequest,
    AgentPatchRequest,
    AgentResponse,
)
from fastapi import APIRouter, Depends, HTTPException, status

router = APIRouter(prefix="/agents", tags=["agents"])


def _to_response(model: AgentProfile) -> AgentResponse:
    """Project ORM row to response model."""
    return AgentResponse.model_validate(model)


@router.post("", response_model=AgentResponse, status_code=status.HTTP_201_CREATED)
async def create_agent(
    request: AgentCreateRequest,
    service: AgentService = Depends(get_agent_service),
) -> AgentResponse:
    """Create an agent profile."""
    now = now_utc()
    payload = request.model_dump()
    payload.update({"created_at": now, "updated_at": now})
    model = await service.create_agent(payload)
    return _to_response(model)


@router.get("", response_model=list[AgentResponse])
async def list_agents(
    service: AgentService = Depends(get_agent_service),
) -> list[AgentResponse]:
    """List all agent profiles."""
    rows = await service.list_agents()
    return [_to_response(row) for row in rows]


@router.get("/{agent_id}", response_model=AgentResponse)
async def get_agent(
    agent_id: int,
    service: AgentService = Depends(get_agent_service),
) -> AgentResponse:
    """Get one profile."""
    model = await service.get_agent(agent_id)
    if model is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found"
        )
    return _to_response(model)


@router.patch("/{agent_id}", response_model=AgentResponse)
async def patch_agent(
    agent_id: int,
    request: AgentPatchRequest,
    service: AgentService = Depends(get_agent_service),
) -> AgentResponse:
    """Patch one profile."""
    payload = request.model_dump(exclude_none=True)
    payload["updated_at"] = now_utc()
    model = await service.update_agent(agent_id, payload)
    return _to_response(model)


@router.delete("/{agent_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_agent(
    agent_id: int,
    service: AgentService = Depends(get_agent_service),
) -> None:
    """Delete one profile."""
    await service.delete_agent(agent_id)
