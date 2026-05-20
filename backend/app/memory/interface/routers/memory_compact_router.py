"""Routes for Memory Compact artifacts."""

from __future__ import annotations

from app.container import ApplicationContainer
from app.memory.application.memory_compact_service import MemoryCompactService
from app.memory.domain.event_enum.memory_compact_enums import (
    MemoryCompactStatus,
)
from app.memory.interface.schemas.memory_compact.memory_compact_schema import (
    MemoryCompactCreateRequest,
    MemoryCompactListResponse,
    MemoryCompactResponse,
)
from app.shared.exceptions.exception_decorators import router_exception_status
from app.shared.exceptions.route_exceptions import (
    MEMORY_COMPACT_ROUTE_EXCEPTION_MAPPING,
)
from app.shared.schemas.datetime_schemas import AwareTimestamp
from dependency_injector.wiring import Provide, inject
from fastapi import APIRouter, Depends, Query, status

router = APIRouter(prefix="/memory/compacts", tags=["memory-compacts"])


@router.get(
    "",
    response_model=MemoryCompactListResponse,
    status_code=status.HTTP_200_OK,
    summary="List Memory Compacts",
    description="List durable Memory Compact artifacts with optional project and status filters.",
)
@router_exception_status(MEMORY_COMPACT_ROUTE_EXCEPTION_MAPPING)
@inject
async def list_memory_compacts(
    project: str | None = Query(default=None),
    compact_status: MemoryCompactStatus | None = Query(default=None, alias="status"),
    covered_after: AwareTimestamp | None = Query(default=None),
    covered_before: AwareTimestamp | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    service: MemoryCompactService = Depends(
        Provide[ApplicationContainer.memory.memory_compact_service]
    ),
) -> MemoryCompactListResponse:
    """List Memory Compact artifacts.

    Args:
        project: Project filter.
        compact_status: Lifecycle status filter.
        covered_after: Coverage-overlap lower bound.
        covered_before: Coverage-overlap upper bound.
        limit: Maximum number of rows to return.
        offset: Number of rows to skip.
        service: Memory Compact application service.

    Returns:
        Paginated Memory Compact response.
    """
    items, total = await service.list_compacts(
        project=project,
        status=compact_status,
        covered_after=covered_after,
        covered_before=covered_before,
        limit=limit,
        offset=offset,
    )
    return MemoryCompactListResponse(
        items=[MemoryCompactResponse.from_entity(item) for item in items],
        total=total,
    )


@router.get(
    "/current",
    response_model=MemoryCompactResponse,
    status_code=status.HTTP_200_OK,
    summary="Get current Memory Compact",
    description="Read the CURRENT Memory Compact for a project or the default project.",
)
@router_exception_status(MEMORY_COMPACT_ROUTE_EXCEPTION_MAPPING)
@inject
async def get_current_memory_compact(
    project: str | None = Query(default=None),
    service: MemoryCompactService = Depends(
        Provide[ApplicationContainer.memory.memory_compact_service]
    ),
) -> MemoryCompactResponse:
    """Read current Memory Compact for a project.

    Args:
        project: Optional project filter; None addresses the default project.
        service: Memory Compact application service.

    Returns:
        Current Memory Compact response.
    """
    compact = await service.current(project=project)
    return MemoryCompactResponse.from_entity(compact)


@router.get(
    "/{compact_id}",
    response_model=MemoryCompactResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Memory Compact",
    description="Read one selected Memory Compact artifact by identifier.",
)
@router_exception_status(MEMORY_COMPACT_ROUTE_EXCEPTION_MAPPING)
@inject
async def get_memory_compact(
    compact_id: str,
    service: MemoryCompactService = Depends(
        Provide[ApplicationContainer.memory.memory_compact_service]
    ),
) -> MemoryCompactResponse:
    """Read one Memory Compact.

    Args:
        compact_id: Memory Compact identifier.
        service: Memory Compact application service.

    Returns:
        Selected Memory Compact response.
    """
    compact = await service.get(compact_id)
    return MemoryCompactResponse.from_entity(compact)


@router.post(
    "",
    response_model=MemoryCompactResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create Memory Compact",
    description="Create a durable Memory Compact artifact and optional source references.",
)
@router_exception_status(MEMORY_COMPACT_ROUTE_EXCEPTION_MAPPING)
@inject
async def create_memory_compact(
    request: MemoryCompactCreateRequest,
    service: MemoryCompactService = Depends(
        Provide[ApplicationContainer.memory.memory_compact_service]
    ),
) -> MemoryCompactResponse:
    """Create a Memory Compact artifact.

    Args:
        request: Public Memory Compact creation payload.
        service: Memory Compact application service.

    Returns:
        Created Memory Compact response.
    """
    compact = await service.create(request.to_create())
    return MemoryCompactResponse.from_entity(compact)


@router.post(
    "/{compact_id}/mark-current",
    response_model=MemoryCompactResponse,
    status_code=status.HTTP_200_OK,
    summary="Mark Memory Compact current",
    description="Promote one compact to CURRENT and supersede the prior current compact for that project.",
)
@router_exception_status(MEMORY_COMPACT_ROUTE_EXCEPTION_MAPPING)
@inject
async def mark_memory_compact_current(
    compact_id: str,
    service: MemoryCompactService = Depends(
        Provide[ApplicationContainer.memory.memory_compact_service]
    ),
) -> MemoryCompactResponse:
    """Mark one compact as current.

    Args:
        compact_id: Memory Compact identifier.
        service: Memory Compact application service.

    Returns:
        Updated current Memory Compact response.
    """
    compact = await service.mark_current(compact_id)
    return MemoryCompactResponse.from_entity(compact)


@router.post(
    "/{compact_id}/archive",
    response_model=MemoryCompactResponse,
    status_code=status.HTTP_200_OK,
    summary="Archive Memory Compact",
    description="Archive a Memory Compact without deleting its durable source references.",
)
@router_exception_status(MEMORY_COMPACT_ROUTE_EXCEPTION_MAPPING)
@inject
async def archive_memory_compact(
    compact_id: str,
    service: MemoryCompactService = Depends(
        Provide[ApplicationContainer.memory.memory_compact_service]
    ),
) -> MemoryCompactResponse:
    """Archive one Memory Compact.

    Args:
        compact_id: Memory Compact identifier.
        service: Memory Compact application service.

    Returns:
        Archived Memory Compact response.
    """
    compact = await service.archive(compact_id)
    return MemoryCompactResponse.from_entity(compact)
