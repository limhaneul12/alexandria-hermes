"""Routes for Context Vault retrieval and embedding operations."""

from __future__ import annotations

from app.container import ApplicationContainer
from app.memory.application.context_service import ContextService
from app.memory.interface.schemas.context.context_mapping import (
    health_payload,
    pack_payload,
    reindex_payload,
    soft_rebuild_payload,
)
from app.memory.interface.schemas.context.context_schema import (
    ContextPackResponse,
    ContextReindexResponse,
    ContextSearchRequest,
    ContextSoftRebuildResponse,
    RagStatusResponse,
)
from app.shared.exceptions.exception_decorators import router_exception_status
from app.shared.exceptions.route_exceptions import CONTEXT_ROUTE_EXCEPTION_MAPPING
from dependency_injector.wiring import Provide, inject
from fastapi import APIRouter, Depends, Query, status

router = APIRouter(prefix="/memory/contexts", tags=["library-contexts"])


@router.post(
    "/retrieval/search",
    response_model=ContextPackResponse,
    status_code=status.HTTP_200_OK,
    description="Search Context Vault and return a Context Pack.",
    summary="Search contexts",
)
@router_exception_status(CONTEXT_ROUTE_EXCEPTION_MAPPING)
@inject
async def search_contexts(
    request: ContextSearchRequest,
    service: ContextService = Depends(
        Provide[ApplicationContainer.memory.context_service]
    ),
) -> ContextPackResponse:
    """Search contexts for RAG.

    Args:
        request: Context search request.
        service: Context application service.

    Returns:
        Context Pack response.
    """
    pack = await service.search(
        query=request.query,
        strategy=request.strategy,
        limit=request.limit,
        project=request.project,
        kind=request.kind,
        include_scopes=request.include_scopes,
        workspace_id=request.workspace_id,
        agent_id=request.agent_id,
        user_id=request.user_id,
        session_id=request.session_id,
        include_lifecycle_statuses=request.include_lifecycle_statuses,
    )
    response = ContextPackResponse.model_validate(pack_payload(pack))
    return response


@router.get(
    "/rag/status",
    response_model=RagStatusResponse,
    status_code=status.HTTP_200_OK,
    description="Return Context RAG dependency health.",
    summary="Get context RAG status",
)
@router_exception_status(CONTEXT_ROUTE_EXCEPTION_MAPPING)
@inject
async def rag_status(
    service: ContextService = Depends(
        Provide[ApplicationContainer.memory.context_service]
    ),
) -> RagStatusResponse:
    """Return RAG dependency status.

    Args:
        service: Context application service.

    Returns:
        RAG health response.
    """
    health = await service.rag_health_with_index_status()
    response = RagStatusResponse.model_validate(health_payload(health))
    return response


@router.post(
    "/retrieval/reindex",
    response_model=ContextReindexResponse,
    status_code=status.HTTP_200_OK,
    description="Backfill embeddings for existing Context Vault chunks.",
    summary="Reindex context embeddings",
)
@router_exception_status(CONTEXT_ROUTE_EXCEPTION_MAPPING)
@inject
async def reindex_context_embeddings(
    limit: int = Query(default=100, ge=1, le=1000),
    force: bool = Query(default=False),
    service: ContextService = Depends(
        Provide[ApplicationContainer.memory.context_service]
    ),
) -> ContextReindexResponse:
    """Backfill embeddings for stored contexts.

    Args:
        limit: Maximum chunks to reindex in this batch.
        force: Whether to rebuild existing embeddings even if model metadata matches.
        service: Context application service.

    Returns:
        Reindex result response.
    """
    result = await service.reindex_embeddings(limit=limit, force=force)
    response = ContextReindexResponse.model_validate(reindex_payload(result))
    return response


@router.post(
    "/retrieval/soft-rebuild",
    response_model=ContextSoftRebuildResponse,
    status_code=status.HTTP_200_OK,
    description="Soft rebuild embeddings/vectors without deleting source rows.",
    summary="Soft rebuild context embeddings",
)
@router_exception_status(CONTEXT_ROUTE_EXCEPTION_MAPPING)
@inject
async def soft_rebuild_context_embeddings(
    limit: int = Query(default=100, ge=1, le=1000),
    verification_query: str | None = Query(default=None),
    project: str | None = Query(default=None),
    service: ContextService = Depends(
        Provide[ApplicationContainer.memory.context_service]
    ),
) -> ContextSoftRebuildResponse:
    """Soft rebuild embedding/vector fields and return operator evidence.

    Args:
        limit: Maximum chunks to rebuild in this batch.
        verification_query: Optional verification query to run after rebuild.
        project: Optional project filter for verification.
        service: Context application service.

    Returns:
        Soft rebuild evidence response.
    """
    result = await service.soft_rebuild_embeddings(
        limit=limit,
        verification_query=verification_query,
        project=project,
    )
    response = ContextSoftRebuildResponse.model_validate(soft_rebuild_payload(result))
    return response
