"""Routes for operational readiness diagnostics."""

from __future__ import annotations

from dependency_injector.wiring import Provide, inject
from fastapi import APIRouter, Depends, status

from app.container import ApplicationContainer
from app.memory.application.context_service import ContextService
from app.obsidian.application.obsidian_service import ObsidianService
from app.operations.application.operational_readiness_service import (
    OperationalReadinessService,
)
from app.operations.interface.schemas.operations.operational_readiness_schema import (
    OperationalReadinessSnapshotResponse,
)
from app.shared.infrastructure.database import Database

router = APIRouter(prefix="/operations", tags=["operations"])


@router.get(
    "/readiness",
    response_model=OperationalReadinessSnapshotResponse,
    status_code=status.HTTP_200_OK,
    summary="Get operational readiness",
    description="Return read-only database, vault, and RAG readiness diagnostics.",
)
@inject
async def operational_readiness(
    database: Database = Depends(Provide[ApplicationContainer.database]),
    context_service: ContextService = Depends(
        Provide[ApplicationContainer.memory.context_service]
    ),
    obsidian_service: ObsidianService = Depends(
        Provide[ApplicationContainer.obsidian.obsidian_service]
    ),
) -> OperationalReadinessSnapshotResponse:
    """Return operational readiness snapshot.

    Args:
        database: Shared database coordinator.
        context_service: Context/RAG service.
        obsidian_service: Obsidian vault service.

    Returns:
        Read-only operational readiness response.
    """
    service = OperationalReadinessService(
        database=database,
        context_service=context_service,
        obsidian_service=obsidian_service,
    )
    snapshot = await service.snapshot()
    return OperationalReadinessSnapshotResponse.from_entity(snapshot)
