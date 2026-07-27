"""Memory reconciliation preview, apply, audit, and conflict routes."""

from __future__ import annotations

from app.container import ApplicationContainer
from app.memory.application.reconciliation.memory_compact_reconciliation_service import (
    MemoryCompactReconciliationService,
)
from app.memory.application.reconciliation.memory_conflict_service import (
    MemoryConflictService,
)
from app.memory.application.reconciliation.memory_reconciliation_apply_service import (
    MemoryReconciliationApplyService,
)
from app.memory.application.reconciliation.memory_reconciliation_preview_service import (
    MemoryReconciliationPreviewService,
)
from app.memory.application.reconciliation.memory_reconciliation_query_service import (
    MemoryReconciliationQueryService,
)
from app.memory.application.reconciliation.memory_temporal_recall_service import (
    MemoryTemporalRecallService,
)
from app.memory.domain.event_enum.reconciliation_enums import MemoryConflictStatus
from app.memory.interface.schemas.reconciliation.memory_reconciliation_candidate_request_schema import (
    MemoryReconciliationApplyRequest,
    MemoryReconciliationPreviewHttpRequest,
)
from app.memory.interface.schemas.reconciliation.memory_reconciliation_compact_response_schema import (
    MemoryCompactSafetyReviewResponse,
)
from app.memory.interface.schemas.reconciliation.memory_reconciliation_conflict_request_schema import (
    MemoryConflictResolutionRequest,
)
from app.memory.interface.schemas.reconciliation.memory_reconciliation_conflict_response_schema import (
    MemoryConflictListResponse,
    MemoryConflictResponse,
)
from app.memory.interface.schemas.reconciliation.memory_reconciliation_plan_response_schema import (
    MemoryReconciliationPlanResponse,
    MemoryReconciliationResultResponse,
    MemoryReviewQueueResponse,
)
from app.memory.interface.schemas.reconciliation.memory_reconciliation_temporal_request_schema import (
    MemoryTemporalRecallHttpRequest,
)
from app.memory.interface.schemas.reconciliation.memory_reconciliation_temporal_response_schema import (
    MemoryTemporalRecallResponse,
)
from app.shared.exceptions.exception_decorators import router_exception_status
from app.shared.exceptions.route_exceptions import CONTEXT_ROUTE_EXCEPTION_MAPPING
from app.shared.types.types_convert_utils import enum_value
from dependency_injector.wiring import Provide, inject
from fastapi import APIRouter, Depends, Query, status

router = APIRouter(
    prefix="/memory/reconciliation",
    tags=["memory-reconciliation"],
)


@router.get(
    "/review-queue",
    response_model=MemoryReviewQueueResponse,
    status_code=status.HTTP_200_OK,
    summary="List memory reconciliation review queue",
    description=(
        "Return persisted reconciliation plans that require explicit review. "
        "Conflict review remains available through the conflict endpoints."
    ),
)
@router_exception_status(CONTEXT_ROUTE_EXCEPTION_MAPPING)
@inject
async def list_memory_reconciliation_review_queue(
    limit: int = Query(default=100, ge=1, le=1000),
    service: MemoryReconciliationQueryService = Depends(
        Provide[ApplicationContainer.memory.reconciliation_query_service]
    ),
) -> MemoryReviewQueueResponse:
    """Return durable UNKNOWN and other review-required plans.

    Args:
        limit: Limit.
        service: Service.

    Returns:
        MemoryReviewQueueResponse: Operation result.
    """
    return MemoryReviewQueueResponse.from_entities(
        await service.list_review_plans(limit=limit)
    )


@router.post(
    "/preview",
    response_model=MemoryReconciliationPlanResponse,
    status_code=status.HTTP_200_OK,
    summary="Preview memory reconciliation",
    description="Create and persist an idempotent plan without canonical mutations.",
)
@router_exception_status(CONTEXT_ROUTE_EXCEPTION_MAPPING)
@inject
async def preview_memory_reconciliation(
    request: MemoryReconciliationPreviewHttpRequest,
    service: MemoryReconciliationPreviewService = Depends(
        Provide[ApplicationContainer.memory.reconciliation_preview_service]
    ),
) -> MemoryReconciliationPlanResponse:
    """Preview one candidate against existing Context memory.

    Args:
        request: Request.
        service: Service.

    Returns:
        MemoryReconciliationPlanResponse: Operation result.
    """
    plan = await service.preview(request.to_contract())
    return MemoryReconciliationPlanResponse.from_entity(plan)


@router.post(
    "/recall",
    response_model=MemoryTemporalRecallResponse,
    status_code=status.HTTP_200_OK,
    summary="Recall memory by temporal perspective",
    description=(
        "Return current, historical, or all matching Contexts with conflict and "
        "supersession metadata."
    ),
)
@router_exception_status(CONTEXT_ROUTE_EXCEPTION_MAPPING)
@inject
async def recall_memory_temporally(
    request: MemoryTemporalRecallHttpRequest,
    service: MemoryTemporalRecallService = Depends(
        Provide[ApplicationContainer.memory.memory_temporal_recall_service]
    ),
) -> MemoryTemporalRecallResponse:
    """Recall Contexts without collapsing temporal or conflict state.

    Args:
        request: Request.
        service: Service.

    Returns:
        MemoryTemporalRecallResponse: Operation result.
    """
    return MemoryTemporalRecallResponse.from_entity(
        await service.recall(request.to_contract())
    )


@router.post(
    "/compact/preview",
    response_model=MemoryCompactSafetyReviewResponse,
    status_code=status.HTTP_200_OK,
    summary="Preview reconciliation-aware Memory Compact input",
    description=(
        "Recall all temporal states, separate current, historical, conflict, "
        "uncertain, and superseded facts, and report publication safety issues."
    ),
)
@router_exception_status(CONTEXT_ROUTE_EXCEPTION_MAPPING)
@inject
async def preview_reconciliation_aware_memory_compact(
    request: MemoryTemporalRecallHttpRequest,
    service: MemoryCompactReconciliationService = Depends(
        Provide[ApplicationContainer.memory.memory_compact_reconciliation_service]
    ),
) -> MemoryCompactSafetyReviewResponse:
    """Prepare safe fact buckets without creating or publishing a compact.

    Args:
        request: Request.
        service: Service.

    Returns:
        MemoryCompactSafetyReviewResponse: Operation result.
    """
    return MemoryCompactSafetyReviewResponse.from_entity(
        await service.prepare(request.to_contract())
    )


@router.get(
    "/plans/{plan_id}",
    response_model=MemoryReconciliationPlanResponse,
    status_code=status.HTTP_200_OK,
    summary="Get reconciliation plan",
)
@router_exception_status(CONTEXT_ROUTE_EXCEPTION_MAPPING)
@inject
async def get_memory_reconciliation_plan(
    plan_id: str,
    service: MemoryReconciliationQueryService = Depends(
        Provide[ApplicationContainer.memory.reconciliation_query_service]
    ),
) -> MemoryReconciliationPlanResponse:
    """Return one persisted reconciliation plan.

    Args:
        plan_id: Plan id.
        service: Service.

    Returns:
        MemoryReconciliationPlanResponse: Operation result.
    """
    return MemoryReconciliationPlanResponse.from_entity(await service.get_plan(plan_id))


@router.post(
    "/plans/{plan_id}/apply",
    response_model=MemoryReconciliationResultResponse,
    status_code=status.HTTP_200_OK,
    summary="Apply reconciliation plan",
    description="Apply one plan idempotently or explicitly retry a failed execution.",
)
@router_exception_status(CONTEXT_ROUTE_EXCEPTION_MAPPING)
@inject
async def apply_memory_reconciliation(
    plan_id: str,
    request: MemoryReconciliationApplyRequest,
    service: MemoryReconciliationApplyService = Depends(
        Provide[ApplicationContainer.memory.reconciliation_apply_service]
    ),
) -> MemoryReconciliationResultResponse:
    """Apply one persisted reconciliation plan.

    Args:
        plan_id: Plan id.
        request: Request.
        service: Service.

    Returns:
        MemoryReconciliationResultResponse: Operation result.
    """
    result = await service.apply(plan_id, retry_failed=request.retry_failed)
    return MemoryReconciliationResultResponse.from_entity(result)


@router.get(
    "/results/{reconciliation_id}",
    response_model=MemoryReconciliationResultResponse,
    status_code=status.HTTP_200_OK,
    summary="Get reconciliation result",
)
@router_exception_status(CONTEXT_ROUTE_EXCEPTION_MAPPING)
@inject
async def get_memory_reconciliation_result(
    reconciliation_id: str,
    service: MemoryReconciliationQueryService = Depends(
        Provide[ApplicationContainer.memory.reconciliation_query_service]
    ),
) -> MemoryReconciliationResultResponse:
    """Return one persisted reconciliation execution result.

    Args:
        reconciliation_id: Reconciliation id.
        service: Service.

    Returns:
        MemoryReconciliationResultResponse: Operation result.
    """
    return MemoryReconciliationResultResponse.from_entity(
        await service.get_result(reconciliation_id)
    )


@router.get(
    "/conflicts",
    response_model=MemoryConflictListResponse,
    status_code=status.HTTP_200_OK,
    summary="List memory conflicts",
)
@router_exception_status(CONTEXT_ROUTE_EXCEPTION_MAPPING)
@inject
async def list_memory_conflicts(
    conflict_status: MemoryConflictStatus | None = Query(default=None, alias="status"),
    limit: int = Query(default=100, ge=1, le=1000),
    service: MemoryConflictService = Depends(
        Provide[ApplicationContainer.memory.memory_conflict_service]
    ),
) -> MemoryConflictListResponse:
    """List unresolved or resolved first-class memory conflicts.

    Args:
        conflict_status: Conflict status.
        limit: Limit.
        service: Service.

    Returns:
        MemoryConflictListResponse: Operation result.
    """
    normalized_status = (
        None
        if conflict_status is None
        else enum_value(conflict_status, MemoryConflictStatus, "status")
    )
    conflicts = await service.list(status=normalized_status, limit=limit)
    items = [MemoryConflictResponse.from_entity(item) for item in conflicts]
    return MemoryConflictListResponse(items=items, total=len(items))


@router.get(
    "/conflicts/{conflict_set_id}",
    response_model=MemoryConflictResponse,
    status_code=status.HTTP_200_OK,
    summary="Get memory conflict",
)
@router_exception_status(CONTEXT_ROUTE_EXCEPTION_MAPPING)
@inject
async def get_memory_conflict(
    conflict_set_id: str,
    service: MemoryConflictService = Depends(
        Provide[ApplicationContainer.memory.memory_conflict_service]
    ),
) -> MemoryConflictResponse:
    """Return one durable memory conflict set.

    Args:
        conflict_set_id: Conflict set id.
        service: Service.

    Returns:
        MemoryConflictResponse: Operation result.
    """
    return MemoryConflictResponse.from_entity(await service.get(conflict_set_id))


@router.post(
    "/conflicts/{conflict_set_id}/reviewing",
    response_model=MemoryConflictResponse,
    status_code=status.HTTP_200_OK,
    summary="Review memory conflict",
)
@router_exception_status(CONTEXT_ROUTE_EXCEPTION_MAPPING)
@inject
async def mark_memory_conflict_reviewing(
    conflict_set_id: str,
    service: MemoryConflictService = Depends(
        Provide[ApplicationContainer.memory.memory_conflict_service]
    ),
) -> MemoryConflictResponse:
    """Mark one open conflict as actively under review.

    Args:
        conflict_set_id: Conflict set id.
        service: Service.

    Returns:
        MemoryConflictResponse: Operation result.
    """
    return MemoryConflictResponse.from_entity(
        await service.mark_reviewing(conflict_set_id)
    )


@router.post(
    "/conflicts/{conflict_set_id}/resolve",
    response_model=MemoryConflictResponse,
    status_code=status.HTTP_200_OK,
    summary="Resolve memory conflict",
)
@router_exception_status(CONTEXT_ROUTE_EXCEPTION_MAPPING)
@inject
async def resolve_memory_conflict(
    conflict_set_id: str,
    request: MemoryConflictResolutionRequest,
    service: MemoryConflictService = Depends(
        Provide[ApplicationContainer.memory.memory_conflict_service]
    ),
) -> MemoryConflictResponse:
    """Record an explicit final conflict resolution without deleting memory.

    Args:
        conflict_set_id: Conflict set id.
        request: Request.
        service: Service.

    Returns:
        MemoryConflictResponse: Operation result.
    """
    resolved = await service.resolve(
        conflict_set_id,
        status=enum_value(request.status, MemoryConflictStatus, "status"),
        resolution=request.resolution,
    )
    return MemoryConflictResponse.from_entity(resolved)
