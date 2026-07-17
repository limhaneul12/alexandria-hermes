"""Routes for recovery run execution."""

from __future__ import annotations

from dependency_injector.wiring import Provide, inject
from fastapi import APIRouter, Depends, HTTPException, status

from app.container import ApplicationContainer
from app.memory.application.context_service import ContextService
from app.obsidian.application.obsidian_service import ObsidianService
from app.operations.application.recovery_run_service import (
    RecoveryInProgressError,
    RecoveryRunService,
)
from app.operations.interface.schemas.operations.recovery_run_schema import (
    RecoveryQuarantineInventoryResponse,
    RecoveryRunRequestSchema,
    RecoveryRunResponse,
    RecoveryRunRetryRequestSchema,
)
from app.shared.infrastructure.database import Database

router = APIRouter(prefix="/operations/recovery", tags=["operations"])


@router.post(
    "/runs",
    response_model=RecoveryRunResponse,
    status_code=status.HTTP_200_OK,
    summary="Start operational recovery",
    description="Run manual recovery when the dry-run plan allows execution.",
)
@inject
async def recovery_run(
    request: RecoveryRunRequestSchema,
    database: Database = Depends(Provide[ApplicationContainer.database]),
    context_service: ContextService = Depends(
        Provide[ApplicationContainer.memory.context_service]
    ),
    obsidian_service: ObsidianService = Depends(
        Provide[ApplicationContainer.obsidian.obsidian_service]
    ),
) -> RecoveryRunResponse:
    """Start or return an idempotent recovery run.

    Args:
        request: Recovery run request payload.
        database: Shared database coordinator.
        context_service: Context/RAG service.
        obsidian_service: Obsidian vault service.

    Returns:
        Recovery run response.
    """
    service = RecoveryRunService(
        database=database,
        context_service=context_service,
        obsidian_service=obsidian_service,
    )
    try:
        run = await service.start(request.to_contract())
    except RecoveryInProgressError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "RECOVERY_IN_PROGRESS",
                "active_recovery_run_id": exc.run_id,
                "idempotency_key": exc.idempotency_key,
            },
        ) from exc
    return RecoveryRunResponse.from_entity(run)


@router.post(
    "/runs/{run_id}/retry",
    response_model=RecoveryRunResponse,
    status_code=status.HTTP_200_OK,
    summary="Retry operational recovery run",
    description="Start a new parent-linked retry for a persisted recovery run.",
)
@inject
async def retry_recovery_run(
    run_id: str,
    request: RecoveryRunRetryRequestSchema,
    database: Database = Depends(Provide[ApplicationContainer.database]),
    context_service: ContextService = Depends(
        Provide[ApplicationContainer.memory.context_service]
    ),
    obsidian_service: ObsidianService = Depends(
        Provide[ApplicationContainer.obsidian.obsidian_service]
    ),
) -> RecoveryRunResponse:
    """Retry a persisted recovery run.

    Args:
        run_id: Parent recovery run identifier.
        request: Retry recovery run request payload.
        database: Shared database coordinator.
        context_service: Context/RAG service.
        obsidian_service: Obsidian vault service.

    Returns:
        Recovery run response.
    """
    service = RecoveryRunService(
        database=database,
        context_service=context_service,
        obsidian_service=obsidian_service,
    )
    try:
        run = await service.retry(run_id, request.to_contract())
    except RecoveryInProgressError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "RECOVERY_IN_PROGRESS",
                "active_recovery_run_id": exc.run_id,
                "idempotency_key": exc.idempotency_key,
            },
        ) from exc
    if run is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "RECOVERY_RUN_NOT_FOUND",
                "run_id": run_id,
            },
        )
    return RecoveryRunResponse.from_entity(run)


@router.get(
    "/runs/{run_id}",
    response_model=RecoveryRunResponse,
    status_code=status.HTTP_200_OK,
    summary="Get operational recovery run",
    description="Return a persisted recovery run manifest by id.",
)
@inject
async def get_recovery_run(
    run_id: str,
    database: Database = Depends(Provide[ApplicationContainer.database]),
    context_service: ContextService = Depends(
        Provide[ApplicationContainer.memory.context_service]
    ),
    obsidian_service: ObsidianService = Depends(
        Provide[ApplicationContainer.obsidian.obsidian_service]
    ),
) -> RecoveryRunResponse:
    """Return persisted recovery run by id.

    Args:
        run_id: Recovery run identifier.
        database: Shared database coordinator.
        context_service: Context/RAG service.
        obsidian_service: Obsidian vault service.

    Returns:
        Recovery run response.
    """
    service = RecoveryRunService(
        database=database,
        context_service=context_service,
        obsidian_service=obsidian_service,
    )
    run = await service.get(run_id)
    if run is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "RECOVERY_RUN_NOT_FOUND",
                "run_id": run_id,
            },
        )
    return RecoveryRunResponse.from_entity(run)


@router.get(
    "/quarantine",
    response_model=RecoveryQuarantineInventoryResponse,
    status_code=status.HTTP_200_OK,
    summary="List recovery quarantine artifacts",
    description="Return stored recovery quarantine artifacts without deleting files.",
)
@inject
async def recovery_quarantine(
    database: Database = Depends(Provide[ApplicationContainer.database]),
    context_service: ContextService = Depends(
        Provide[ApplicationContainer.memory.context_service]
    ),
    obsidian_service: ObsidianService = Depends(
        Provide[ApplicationContainer.obsidian.obsidian_service]
    ),
) -> RecoveryQuarantineInventoryResponse:
    """Return recovery quarantine inventory.

    Args:
        database: Shared database coordinator.
        context_service: Context/RAG service.
        obsidian_service: Obsidian vault service.

    Returns:
        Quarantine inventory response.
    """
    service = RecoveryRunService(
        database=database,
        context_service=context_service,
        obsidian_service=obsidian_service,
    )
    items = await service.quarantine_inventory()
    return RecoveryQuarantineInventoryResponse.from_entities(items)
