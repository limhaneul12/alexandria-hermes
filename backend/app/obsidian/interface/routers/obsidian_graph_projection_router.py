"""Routes for the optional Obsidian graph projection read model."""

from __future__ import annotations

from app.container import ApplicationContainer
from app.obsidian.application.graph.obsidian_graph_projection_rebuild_service import (
    ObsidianGraphProjectionRebuildService,
)
from app.obsidian.interface.schemas.obsidian.obsidian_graph_projection_schema import (
    ObsidianGraphProjectionRebuildResponse,
    ObsidianGraphProjectionStatusResponse,
)
from app.shared.exceptions.exception_decorators import router_exception_status
from app.shared.exceptions.route_exceptions import OBSIDIAN_ROUTE_EXCEPTION_MAPPING
from dependency_injector.wiring import Provide, inject
from fastapi import APIRouter, Depends, Query, status

router = APIRouter()


@router.get(
    "/graph/projection/status",
    response_model=ObsidianGraphProjectionStatusResponse,
    status_code=status.HTTP_200_OK,
    summary="Get optional graph projection status",
    description="Return status for the rebuildable optional Neo4j graph projection.",
)
@inject
async def graph_projection_status(
    service: ObsidianGraphProjectionRebuildService = Depends(
        Provide[ApplicationContainer.obsidian.graph_projection_rebuild_service]
    ),
) -> ObsidianGraphProjectionStatusResponse:
    """Return graph projection status without mutating Markdown.

    Args:
        service: Graph projection rebuild/status service.

    Returns:
        Current graph projection status response.
    """
    report = await service.status()
    return ObsidianGraphProjectionStatusResponse.from_entity(report)


@router.post(
    "/graph/projection/rebuild",
    response_model=ObsidianGraphProjectionRebuildResponse,
    status_code=status.HTTP_200_OK,
    summary="Rebuild optional graph projection",
    description=(
        "Explicitly rebuild the optional Neo4j graph projection from the "
        "existing read-only Obsidian/SQLite index state."
    ),
)
@router_exception_status(OBSIDIAN_ROUTE_EXCEPTION_MAPPING)
@inject
async def rebuild_graph_projection(
    include_issue_details: bool = Query(default=False),
    issue_limit: int = Query(default=100, ge=1, le=500),
    service: ObsidianGraphProjectionRebuildService = Depends(
        Provide[ApplicationContainer.obsidian.graph_projection_rebuild_service]
    ),
) -> ObsidianGraphProjectionRebuildResponse:
    """Rebuild graph projection without mutating canonical Markdown.

    Args:
        service: Graph projection rebuild/status service.

    Returns:
        Rebuild operation response.
    """
    report = await service.rebuild(
        include_issue_details=include_issue_details,
        issue_limit=issue_limit,
    )
    return ObsidianGraphProjectionRebuildResponse.from_entity(report)
