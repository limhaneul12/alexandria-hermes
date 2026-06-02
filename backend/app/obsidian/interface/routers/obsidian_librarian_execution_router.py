"""Routes for Obsidian librarian execution operations."""

from __future__ import annotations

from app.container import ApplicationContainer
from app.obsidian.application.obsidian_librarian_job_service import (
    ObsidianLibrarianJobService,
)
from app.obsidian.application.obsidian_service import ObsidianService
from app.obsidian.interface.schemas.obsidian.obsidian_librarian_execution_schema import (
    ObsidianLibrarianJobResponse,
    ObsidianVaultInventoryItemResponse,
    ObsidianVaultInventoryRequestSchema,
    ObsidianVaultInventoryResponse,
    ObsidianVaultMoveApplyRequestSchema,
    ObsidianVaultMovePlanRequestSchema,
    ObsidianVaultMovePlanResponse,
    ObsidianVaultMoveReportResponse,
    ObsidianVaultPathSearchRequest,
)
from app.shared.exceptions.exception_decorators import router_exception_status
from app.shared.exceptions.route_exceptions import OBSIDIAN_ROUTE_EXCEPTION_MAPPING
from dependency_injector.wiring import Provide, inject
from fastapi import APIRouter, BackgroundTasks, Depends, status

router = APIRouter(prefix="/obsidian", tags=["obsidian"])


@router.post(
    "/librarian/vault/inventory",
    response_model=ObsidianVaultInventoryResponse,
    status_code=status.HTTP_200_OK,
    summary="Inventory managed Obsidian vault notes",
    description="List managed Markdown notes under a scope for librarian workflows.",
)
@router_exception_status(OBSIDIAN_ROUTE_EXCEPTION_MAPPING)
@inject
async def inventory_obsidian_vault_notes(
    request: ObsidianVaultInventoryRequestSchema,
    service: ObsidianService = Depends(
        Provide[ApplicationContainer.obsidian.obsidian_service]
    ),
) -> ObsidianVaultInventoryResponse:
    """Inventory managed notes for typed librarian execution planning.

    Args:
        request: Inventory scope request.
        service: Obsidian application service.

    Returns:
        Managed note inventory response.
    """
    items = await service.inventory_vault(request.to_command())
    responses = [ObsidianVaultInventoryItemResponse.from_entity(item) for item in items]
    return ObsidianVaultInventoryResponse(items=responses, total=len(responses))


@router.post(
    "/librarian/vault/path-search",
    response_model=ObsidianVaultInventoryResponse,
    status_code=status.HTTP_200_OK,
    summary="Search managed Obsidian vault paths",
    description="Search managed note paths and metadata without relying on FTS.",
)
@router_exception_status(OBSIDIAN_ROUTE_EXCEPTION_MAPPING)
@inject
async def search_obsidian_vault_paths(
    request: ObsidianVaultPathSearchRequest,
    service: ObsidianService = Depends(
        Provide[ApplicationContainer.obsidian.obsidian_service]
    ),
) -> ObsidianVaultInventoryResponse:
    """Search inventory metadata for typed librarian execution planning.

    Args:
        request: Path/metadata search request.
        service: Obsidian application service.

    Returns:
        Matching inventory items.
    """
    items = await service.search_vault_paths(
        query=request.query,
        scope_path=request.scope_path,
    )
    responses = [ObsidianVaultInventoryItemResponse.from_entity(item) for item in items]
    return ObsidianVaultInventoryResponse(items=responses, total=len(responses))


@router.post(
    "/librarian/vault/move-plan",
    response_model=ObsidianVaultMovePlanResponse,
    status_code=status.HTTP_200_OK,
    summary="Plan safe Obsidian vault moves",
    description="Dry-run note moves with no hard delete and no overwrite.",
)
@router_exception_status(OBSIDIAN_ROUTE_EXCEPTION_MAPPING)
@inject
async def plan_obsidian_vault_moves(
    request: ObsidianVaultMovePlanRequestSchema,
    service: ObsidianService = Depends(
        Provide[ApplicationContainer.obsidian.obsidian_service]
    ),
) -> ObsidianVaultMovePlanResponse:
    """Plan safe moves for a typed librarian vault workflow.

    Args:
        request: Requested safe move plan.
        service: Obsidian application service.

    Returns:
        Dry-run move plan.
    """
    plan = await service.plan_vault_moves(request.to_command())
    return ObsidianVaultMovePlanResponse.from_entity(plan)


@router.post(
    "/librarian/vault/apply-moves",
    response_model=ObsidianVaultMoveReportResponse,
    status_code=status.HTTP_200_OK,
    summary="Apply safe Obsidian vault moves",
    description="Apply planned note moves, reindex, verify, and write reports.",
)
@router_exception_status(OBSIDIAN_ROUTE_EXCEPTION_MAPPING)
@inject
async def apply_obsidian_vault_moves(
    request: ObsidianVaultMoveApplyRequestSchema,
    service: ObsidianService = Depends(
        Provide[ApplicationContainer.obsidian.obsidian_service]
    ),
) -> ObsidianVaultMoveReportResponse:
    """Apply safe note moves for a typed librarian vault workflow.

    Args:
        request: Safe move application request.
        service: Obsidian application service.

    Returns:
        Move application report.
    """
    report = await service.apply_vault_moves(request.to_command())
    return ObsidianVaultMoveReportResponse.from_entity(report)


@router.post(
    "/librarian/jobs",
    response_model=ObsidianLibrarianJobResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Start in-process Obsidian librarian execution job",
    description=(
        "Start a best-effort in-process vault organization job and return job_id; "
        "job status is not restart-durable, but report files are written to the vault."
    ),
)
@router_exception_status(OBSIDIAN_ROUTE_EXCEPTION_MAPPING)
@inject
async def start_obsidian_librarian_job(
    request: ObsidianVaultMoveApplyRequestSchema,
    background_tasks: BackgroundTasks,
    job_service: ObsidianLibrarianJobService = Depends(
        Provide[ApplicationContainer.obsidian.job_service]
    ),
) -> ObsidianLibrarianJobResponse:
    """Start a best-effort in-process librarian vault execution job.

    Args:
        request: Safe move application request.
        background_tasks: FastAPI background task collector.
        job_service: Librarian job service.

    Returns:
        Pending job status response.
    """
    job = job_service.create_vault_move_job()
    background_tasks.add_task(
        job_service.run_vault_move_job,
        job_id=job.job_id,
        request=request.to_command(),
    )
    return ObsidianLibrarianJobResponse.from_entity(job)


@router.get(
    "/librarian/jobs/{job_id}",
    response_model=ObsidianLibrarianJobResponse,
    status_code=status.HTTP_200_OK,
    summary="Read Obsidian librarian job status",
    description=(
        "Return status and report handles for an in-process librarian execution job; "
        "unknown ids after restart return not found."
    ),
)
@router_exception_status(OBSIDIAN_ROUTE_EXCEPTION_MAPPING)
@inject
async def get_obsidian_librarian_job(
    job_id: str,
    job_service: ObsidianLibrarianJobService = Depends(
        Provide[ApplicationContainer.obsidian.job_service]
    ),
) -> ObsidianLibrarianJobResponse:
    """Read one best-effort in-process librarian execution job status.

    Args:
        job_id: Librarian job id.
        job_service: Librarian job service.

    Returns:
        Current job status response.
    """
    return ObsidianLibrarianJobResponse.from_entity(job_service.get_job(job_id))


@router.get(
    "/librarian/jobs/{job_id}/report",
    response_model=ObsidianVaultMoveReportResponse,
    status_code=status.HTTP_200_OK,
    summary="Read Obsidian librarian job report",
    description="Return the typed report for a completed librarian execution job.",
)
@router_exception_status(OBSIDIAN_ROUTE_EXCEPTION_MAPPING)
@inject
async def get_obsidian_librarian_job_report(
    job_id: str,
    job_service: ObsidianLibrarianJobService = Depends(
        Provide[ApplicationContainer.obsidian.job_service]
    ),
) -> ObsidianVaultMoveReportResponse:
    """Read one completed librarian execution job report.

    Args:
        job_id: Librarian job id.
        job_service: Librarian job service.

    Returns:
        Completed job move report.
    """
    report = job_service.get_report(job_id)
    return ObsidianVaultMoveReportResponse.from_entity(report)
