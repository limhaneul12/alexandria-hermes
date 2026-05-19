"""Context Vault routes."""

from __future__ import annotations

from app.container import ApplicationContainer
from app.memory.application.context_service import ContextService
from app.memory.domain.contracts.harness_contracts import HarnessCapture
from app.memory.domain.event_enum.context_enums import ContextKind, ContextScope
from app.memory.interface.schemas.context.context_mapping import (
    access_event_payload,
    chunk_payload,
    context_payload,
    health_payload,
    pack_payload,
    reindex_payload,
)
from app.memory.interface.schemas.context.context_metadata_mapping import (
    metadata_payload,
)
from app.memory.interface.schemas.context.context_schema import (
    ContextAccessEventRequest,
    ContextAccessEventResponse,
    ContextAccessEventResponseList,
    ContextCaptureRequest,
    ContextChunkResponseList,
    ContextListResponse,
    ContextPackResponse,
    ContextPrepareCompactRequest,
    ContextReindexResponse,
    ContextResponse,
    ContextSearchRequest,
    HarnessCaptureRequest,
    RagStatusResponse,
)
from app.shared.exceptions import ValidationError
from app.shared.exceptions.exception_decorators import router_exception_status
from app.shared.exceptions.route_exceptions import CONTEXT_ROUTE_EXCEPTION_MAPPING
from dependency_injector.wiring import Provide, inject
from fastapi import APIRouter, Depends, Query, status

router = APIRouter(prefix="/memory/contexts", tags=["library-contexts"])


async def _save_context(
    request: ContextCaptureRequest,
    service: ContextService,
) -> ContextResponse:
    context = await service.save(
        kind=request.kind,
        title=request.title,
        content=request.content,
        summary=request.summary,
        project=request.project,
        scope=request.scope,
        workspace_id=request.workspace_id,
        agent_id=request.agent_id,
        user_id=request.user_id,
        session_id=request.session_id,
        visibility=request.visibility,
        source_agent=request.source_agent,
        source_type=request.source_type,
        importance=request.importance,
        tags=request.tags,
        expires_at=request.expires_at,
        context_metadata=metadata_payload(request.metadata),
    )
    response = ContextResponse.model_validate(context_payload(context))
    return response


@router.get(
    "",
    response_model=ContextListResponse,
    status_code=status.HTTP_200_OK,
    description="List Context Vault entries.",
    summary="List contexts",
)
@router_exception_status(CONTEXT_ROUTE_EXCEPTION_MAPPING)
@inject
async def list_contexts(
    kind: ContextKind | None = Query(default=None),
    project: str | None = Query(default=None),
    scope: ContextScope | None = Query(default=None),
    workspace_id: str | None = Query(default=None),
    agent_id: str | None = Query(default=None),
    user_id: str | None = Query(default=None),
    session_id: str | None = Query(default=None),
    source_agent: str | None = Query(default=None),
    tag: str | None = Query(default=None),
    include_archived: bool = Query(default=False),
    limit: int = Query(default=50, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
    service: ContextService = Depends(
        Provide[ApplicationContainer.memory.context_service]
    ),
) -> ContextListResponse:
    """List contexts.

    Args:
        kind: Optional context kind filter.
        project: Optional project filter.
        scope: Optional context scope filter.
        workspace_id: Optional workspace filter.
        agent_id: Optional agent filter.
        user_id: Optional user filter.
        session_id: Optional session filter.
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
        scope=scope,
        workspace_id=workspace_id,
        agent_id=agent_id,
        user_id=user_id,
        session_id=session_id,
        source_agent=source_agent,
        tag=tag,
        include_archived=include_archived,
    )
    response = ContextListResponse.model_validate(
        {"items": [context_payload(item) for item in items], "total": total}
    )
    return response


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
@router_exception_status(CONTEXT_ROUTE_EXCEPTION_MAPPING)
@inject
async def capture_context(
    request: ContextCaptureRequest,
    service: ContextService = Depends(
        Provide[ApplicationContainer.memory.context_service]
    ),
) -> ContextResponse:
    """Capture context through the same save path.

    Args:
        request: Context capture request.
        service: Context application service.

    Returns:
        Stored context response.
    """
    if request.kind == ContextKind.HARNESS:
        raise ValidationError(
            "HARNESS contexts must be captured through "
            "/memory/contexts/harnesses/capture"
        )
    response = await _save_context(request=request, service=service)
    return response


@router.post(
    "/harnesses/capture",
    response_model=ContextResponse,
    status_code=status.HTTP_201_CREATED,
    description=(
        "Capture an agent-owned execution harness as Context Vault memory. "
        "This is not a human CRUD surface."
    ),
    summary="Capture execution harness",
)
@router_exception_status(CONTEXT_ROUTE_EXCEPTION_MAPPING)
@inject
async def capture_harness(
    request: HarnessCaptureRequest,
    service: ContextService = Depends(
        Provide[ApplicationContainer.memory.context_service]
    ),
) -> ContextResponse:
    """Capture an agent-owned execution harness.

    Args:
        request: Harness capture request.
        service: Context application service.

    Returns:
        Stored HARNESS context response.
    """
    context = await service.capture_harness(
        HarnessCapture(
            task_goal=request.task_goal,
            reusable_procedure=request.reusable_procedure,
            summary=request.summary,
            project=request.project,
            scope=request.scope,
            workspace_id=request.workspace_id,
            agent_id=request.agent_id,
            user_id=request.user_id,
            session_id=request.session_id,
            source_agent=request.source_agent,
            environment=request.environment,
            trigger_context=request.trigger_context,
            steps=request.steps,
            commands=request.commands,
            tests=request.tests,
            failures=request.failures,
            fixes=request.fixes,
            artifacts=request.artifacts,
            recall_keywords=request.recall_keywords,
            safety_notes=request.safety_notes,
            metadata=metadata_payload(request.metadata),
        )
    )
    response = ContextResponse.model_validate(context_payload(context))
    return response


@router.post(
    "/prepare-compact",
    response_model=ContextResponse,
    status_code=status.HTTP_201_CREATED,
    description="Prepare and save a compact handoff context.",
    summary="Prepare compact",
)
@router_exception_status(CONTEXT_ROUTE_EXCEPTION_MAPPING)
@inject
async def prepare_compact(
    request: ContextPrepareCompactRequest,
    service: ContextService = Depends(
        Provide[ApplicationContainer.memory.context_service]
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
        scope=request.scope,
        workspace_id=request.workspace_id,
        agent_id=request.agent_id,
        user_id=request.user_id,
        session_id=request.session_id,
        visibility=request.visibility,
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
    response = RagStatusResponse.model_validate(health_payload(service.rag_health()))
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
    service: ContextService = Depends(
        Provide[ApplicationContainer.memory.context_service]
    ),
) -> ContextReindexResponse:
    """Backfill embeddings for stored contexts.

    Args:
        limit: Maximum chunks to reindex in this batch.
        service: Context application service.

    Returns:
        Reindex result response.
    """
    result = await service.reindex_embeddings(limit=limit)
    response = ContextReindexResponse.model_validate(reindex_payload(result))
    return response


@router.get(
    "/{context_id}/chunks",
    response_model=ContextChunkResponseList,
    status_code=status.HTTP_200_OK,
    description="List stored chunks for one context.",
    summary="List context chunks",
)
@router_exception_status(CONTEXT_ROUTE_EXCEPTION_MAPPING)
@inject
async def context_chunks(
    context_id: str,
    service: ContextService = Depends(
        Provide[ApplicationContainer.memory.context_service]
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


@router.post(
    "/{context_id}/access-events",
    response_model=ContextAccessEventResponse,
    status_code=status.HTTP_201_CREATED,
    description="Record a detailed Context Vault access event.",
    summary="Record context access event",
)
@router_exception_status(CONTEXT_ROUTE_EXCEPTION_MAPPING)
@inject
async def record_context_access_event(
    context_id: str,
    request: ContextAccessEventRequest,
    service: ContextService = Depends(
        Provide[ApplicationContainer.memory.context_service]
    ),
) -> ContextAccessEventResponse:
    """Record one detailed access event and return it.

    Args:
        context_id: Context identifier.
        request: Access-event details.
        service: Context application service.

    Returns:
        Created context access event response.
    """
    await service.access(
        context_id,
        actor_name=request.actor_name,
        actor_type=request.actor_type,
        access_method=request.access_method,
        source_surface=request.source_surface,
    )
    events = await service.access_events(context_id, limit=1)
    response = ContextAccessEventResponse.model_validate(
        access_event_payload(events[0])
    )
    return response


@router.get(
    "/{context_id}/access-events",
    response_model=ContextAccessEventResponseList,
    status_code=status.HTTP_200_OK,
    description="List recent Context Vault access events.",
    summary="List context access events",
)
@router_exception_status(CONTEXT_ROUTE_EXCEPTION_MAPPING)
@inject
async def list_context_access_events(
    context_id: str,
    limit: int = Query(default=5, ge=1, le=5),
    service: ContextService = Depends(
        Provide[ApplicationContainer.memory.context_service]
    ),
) -> ContextAccessEventResponseList:
    """List recent access events for one context.

    Args:
        context_id: Context identifier.
        limit: Maximum returned events.
        service: Context application service.

    Returns:
        Recent context access event responses.
    """
    events = await service.access_events(context_id, limit=limit)
    response = ContextAccessEventResponseList.model_validate(
        [access_event_payload(event) for event in events]
    )
    return response


@router.get(
    "/{context_id}",
    response_model=ContextResponse,
    status_code=status.HTTP_200_OK,
    description="Read one Context Vault entry.",
    summary="Get context",
)
@router_exception_status(CONTEXT_ROUTE_EXCEPTION_MAPPING)
@inject
async def get_context(
    context_id: str,
    service: ContextService = Depends(
        Provide[ApplicationContainer.memory.context_service]
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
@router_exception_status(CONTEXT_ROUTE_EXCEPTION_MAPPING)
@inject
async def access_context(
    context_id: str,
    service: ContextService = Depends(
        Provide[ApplicationContainer.memory.context_service]
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
@router_exception_status(CONTEXT_ROUTE_EXCEPTION_MAPPING)
@inject
async def archive_context(
    context_id: str,
    service: ContextService = Depends(
        Provide[ApplicationContainer.memory.context_service]
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
