"""Context Vault routes."""

from __future__ import annotations

from app.container import ApplicationContainer
from app.library.application.context_service import ContextService
from app.library.domain.event_enum.context_enums import ContextKind
from app.library.interface.schemas.context.context_mapping import (
    chunk_payload,
    context_payload,
    health_payload,
    lint_payload,
    pack_payload,
)
from app.library.interface.schemas.context.context_metadata_mapping import (
    metadata_payload,
)
from app.library.interface.schemas.context.context_schema import (
    ContextCaptureRequest,
    ContextChunkResponseList,
    ContextLintRequest,
    ContextLintResponse,
    ContextListResponse,
    ContextPackResponse,
    ContextPrepareCompactRequest,
    ContextResponse,
    ContextSaveRequest,
    ContextSearchRequest,
    RagStatusResponse,
)
from app.shared.exceptions.exception_decorators import router_exception_status
from app.shared.exceptions.route_exceptions import LIBRARY_ROUTE_EXCEPTION_MAPPING
from dependency_injector.wiring import Provide, inject
from fastapi import APIRouter, Depends, Query, status

router = APIRouter(prefix="/library/contexts", tags=["library-contexts"])


async def _save_context(
    request: ContextSaveRequest,
    service: ContextService,
) -> ContextResponse:
    context = await service.save(
        kind=request.kind,
        title=request.title,
        content=request.content,
        summary=request.summary,
        project=request.project,
        source_agent=request.source_agent,
        source_type=request.source_type,
        importance=request.importance,
        tags=request.tags,
        expires_at=request.expires_at,
        context_metadata=metadata_payload(request.metadata),
    )
    response = ContextResponse.model_validate(context_payload(context))
    return response


@router.post(
    "/lint",
    response_model=ContextLintResponse,
    status_code=status.HTTP_200_OK,
    description="Lint Context Vault content without saving it.",
    summary="Lint context",
)
@router_exception_status(LIBRARY_ROUTE_EXCEPTION_MAPPING)
@inject
async def lint_context(
    request: ContextLintRequest,
    service: ContextService = Depends(
        Provide[ApplicationContainer.library.context_service]
    ),
) -> ContextLintResponse:
    """Lint a context payload.

    Args:
        request: Context lint request.
        service: Context application service.

    Returns:
        Lint result response.
    """
    result = service.lint(
        kind=request.kind,
        title=request.title,
        content=request.content,
        summary=request.summary,
        project=request.project,
        source_agent=request.source_agent,
        tags=request.tags,
    )
    response = ContextLintResponse.model_validate(lint_payload(result))
    return response


@router.post(
    "",
    response_model=ContextResponse,
    status_code=status.HTTP_201_CREATED,
    description="Save a Context Vault entry after linting/redaction.",
    summary="Create context",
)
@router_exception_status(LIBRARY_ROUTE_EXCEPTION_MAPPING)
@inject
async def create_context(
    request: ContextSaveRequest,
    service: ContextService = Depends(
        Provide[ApplicationContainer.library.context_service]
    ),
) -> ContextResponse:
    """Save a context entry.

    Args:
        request: Context save request.
        service: Context application service.

    Returns:
        Stored context response.
    """
    response = await _save_context(request=request, service=service)
    return response


@router.get(
    "",
    response_model=ContextListResponse,
    status_code=status.HTTP_200_OK,
    description="List Context Vault entries.",
    summary="List contexts",
)
@router_exception_status(LIBRARY_ROUTE_EXCEPTION_MAPPING)
@inject
async def list_contexts(
    kind: ContextKind | None = Query(default=None),
    project: str | None = Query(default=None),
    source_agent: str | None = Query(default=None),
    tag: str | None = Query(default=None),
    include_archived: bool = Query(default=False),
    limit: int = Query(default=50, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
    service: ContextService = Depends(
        Provide[ApplicationContainer.library.context_service]
    ),
) -> ContextListResponse:
    """List contexts.

    Args:
        kind: Optional context kind filter.
        project: Optional project filter.
        source_agent: Optional source-agent filter.
        tag: Optional tag filter.
        include_archived: Whether archived entries are included.
        limit: Maximum returned entries.
        offset: Pagination offset.
        service: Context application service.

    Returns:
        Paginated context response.
    """
    items, total = await service.list_contexts(
        limit=limit,
        offset=offset,
        kind=kind,
        project=project,
        source_agent=source_agent,
        tag=tag,
        include_archived=include_archived,
    )
    response = ContextListResponse.model_validate(
        {"items": [context_payload(item) for item in items], "total": total}
    )
    return response


@router.post(
    "/search",
    response_model=ContextPackResponse,
    status_code=status.HTTP_200_OK,
    description="Search Context Vault and return a Context Pack.",
    summary="Search contexts",
)
@router_exception_status(LIBRARY_ROUTE_EXCEPTION_MAPPING)
@inject
async def search_contexts(
    request: ContextSearchRequest,
    service: ContextService = Depends(
        Provide[ApplicationContainer.library.context_service]
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
    )
    response = ContextPackResponse.model_validate(pack_payload(pack))
    return response


@router.post(
    "/capture",
    response_model=ContextResponse,
    status_code=status.HTTP_201_CREATED,
    description="Capture agent working context with Context Vault semantics.",
    summary="Capture context",
)
@router_exception_status(LIBRARY_ROUTE_EXCEPTION_MAPPING)
@inject
async def capture_context(
    request: ContextCaptureRequest,
    service: ContextService = Depends(
        Provide[ApplicationContainer.library.context_service]
    ),
) -> ContextResponse:
    """Capture context through the same save path.

    Args:
        request: Context capture request.
        service: Context application service.

    Returns:
        Stored context response.
    """
    response = await _save_context(request=request, service=service)
    return response


@router.post(
    "/prepare-compact",
    response_model=ContextResponse,
    status_code=status.HTTP_201_CREATED,
    description="Prepare and save a compact handoff context.",
    summary="Prepare compact",
)
@router_exception_status(LIBRARY_ROUTE_EXCEPTION_MAPPING)
@inject
async def prepare_compact(
    request: ContextPrepareCompactRequest,
    service: ContextService = Depends(
        Provide[ApplicationContainer.library.context_service]
    ),
) -> ContextResponse:
    """Build and store a compact context from structured state.

    Args:
        request: Compact preparation request.
        service: Context application service.

    Returns:
        Stored compact context response.
    """
    context = await service.prepare_compact(
        current_goal=request.current_goal,
        completed=request.completed,
        in_progress=request.in_progress,
        key_decisions=request.key_decisions,
        next_actions=request.next_actions,
        risks=request.risks,
        project=request.project,
        source_agent=request.source_agent,
    )
    response = ContextResponse.model_validate(context_payload(context))
    return response


@router.get(
    "/rag/status",
    response_model=RagStatusResponse,
    status_code=status.HTTP_200_OK,
    description="Return Context RAG dependency health.",
    summary="Get context RAG status",
)
@router_exception_status(LIBRARY_ROUTE_EXCEPTION_MAPPING)
@inject
async def rag_status(
    service: ContextService = Depends(
        Provide[ApplicationContainer.library.context_service]
    ),
) -> RagStatusResponse:
    """Return RAG dependency status.

    Args:
        service: Context application service.

    Returns:
        RAG health response.
    """
    response = RagStatusResponse.model_validate(health_payload(service.rag_health()))
    return response


@router.get(
    "/{context_id}/chunks",
    response_model=ContextChunkResponseList,
    status_code=status.HTTP_200_OK,
    description="List stored chunks for one context.",
    summary="List context chunks",
)
@router_exception_status(LIBRARY_ROUTE_EXCEPTION_MAPPING)
@inject
async def context_chunks(
    context_id: str,
    service: ContextService = Depends(
        Provide[ApplicationContainer.library.context_service]
    ),
) -> ContextChunkResponseList:
    """List chunks for one context.

    Args:
        context_id: Context identifier.
        service: Context application service.

    Returns:
        Context chunk list response.
    """
    chunks = await service.chunks(context_id)
    response = ContextChunkResponseList.model_validate(
        [chunk_payload(chunk) for chunk in chunks]
    )
    return response


@router.get(
    "/{context_id}",
    response_model=ContextResponse,
    status_code=status.HTTP_200_OK,
    description="Read one Context Vault entry.",
    summary="Get context",
)
@router_exception_status(LIBRARY_ROUTE_EXCEPTION_MAPPING)
@inject
async def get_context(
    context_id: str,
    service: ContextService = Depends(
        Provide[ApplicationContainer.library.context_service]
    ),
) -> ContextResponse:
    """Get one context.

    Args:
        context_id: Context identifier.
        service: Context application service.

    Returns:
        Stored context response.
    """
    context = await service.get(context_id)
    response = ContextResponse.model_validate(context_payload(context))
    return response


@router.post(
    "/{context_id}/access",
    response_model=ContextResponse,
    status_code=status.HTTP_200_OK,
    description="Record an access event for one context.",
    summary="Access context",
)
@router_exception_status(LIBRARY_ROUTE_EXCEPTION_MAPPING)
@inject
async def access_context(
    context_id: str,
    service: ContextService = Depends(
        Provide[ApplicationContainer.library.context_service]
    ),
) -> ContextResponse:
    """Record access for one context.

    Args:
        context_id: Context identifier.
        service: Context application service.

    Returns:
        Updated context response.
    """
    context = await service.access(context_id)
    response = ContextResponse.model_validate(context_payload(context))
    return response


@router.post(
    "/{context_id}/archive",
    response_model=ContextResponse,
    status_code=status.HTTP_200_OK,
    description="Archive one context; hard delete is intentionally unavailable.",
    summary="Archive context",
)
@router_exception_status(LIBRARY_ROUTE_EXCEPTION_MAPPING)
@inject
async def archive_context(
    context_id: str,
    service: ContextService = Depends(
        Provide[ApplicationContainer.library.context_service]
    ),
) -> ContextResponse:
    """Archive one context.

    Args:
        context_id: Context identifier.
        service: Context application service.

    Returns:
        Archived context response.
    """
    context = await service.archive(context_id)
    response = ContextResponse.model_validate(context_payload(context))
    return response
