"""Routes for recovery dry-run planning."""

from __future__ import annotations

from dependency_injector.wiring import Provide, inject
from fastapi import APIRouter, Depends, status

from app.container import ApplicationContainer
from app.memory.application.context_service import ContextService
from app.obsidian.application.obsidian_service import ObsidianService
from app.operations.application.recovery_plan_service import RecoveryPlanService
from app.operations.interface.schemas.operations.recovery_plan_schema import (
    RecoveryPlanRequestSchema,
    RecoveryPlanResponse,
)
from app.shared.infrastructure.database import Database

router = APIRouter(prefix="/operations/recovery", tags=["operations"])


@router.post(
    "/plan",
    response_model=RecoveryPlanResponse,
    status_code=status.HTTP_200_OK,
    summary="Plan operational recovery",
    description="Return a read-only recovery dry-run plan without mutating files.",
)
@inject
async def recovery_plan(
    request: RecoveryPlanRequestSchema,
    database: Database = Depends(Provide[ApplicationContainer.database]),
    context_service: ContextService = Depends(
        Provide[ApplicationContainer.memory.context_service]
    ),
    obsidian_service: ObsidianService = Depends(
        Provide[ApplicationContainer.obsidian.obsidian_service]
    ),
) -> RecoveryPlanResponse:
    """Return recovery dry-run plan.

    Args:
        request: Recovery plan request payload.
        database: Shared database coordinator.
        context_service: Context/RAG service.
        obsidian_service: Obsidian vault service.

    Returns:
        Recovery dry-run plan response.
    """
    service = RecoveryPlanService(
        database=database,
        context_service=context_service,
        obsidian_service=obsidian_service,
    )
    plan = await service.plan(request.to_contract())
    return RecoveryPlanResponse.from_entity(plan)
