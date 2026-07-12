"""Context Vault routes."""

from __future__ import annotations

from app.container import ApplicationContainer
from app.memory.application.context_service import ContextService
from app.memory.domain.event_enum.context_enums import ContextKind, ContextScope
from app.memory.interface.schemas.context.context_mapping import (
    chunk_payload,
    context_payload,
)
from app.memory.interface.schemas.context.context_schema import (
    ContextChunkResponseList,
    ContextListResponse,
    ContextResponse,
)
from app.shared.exceptions.exception_decorators import router_exception_status
from app.shared.exceptions.route_exceptions import CONTEXT_ROUTE_EXCEPTION_MAPPING
from app.shared.schemas.datetime_schemas import AwareTimestamp
from dependency_injector.wiring import Provide, inject
from fastapi import APIRouter, Depends, Query, Response, status

router = APIRouter(prefix="/memory/contexts", tags=["library-contexts"])


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
    created_after: AwareTimestamp | None = Query(default=None),
    created_before: AwareTimestamp | None = Query(default=None),
    updated_after: AwareTimestamp | None = Query(default=None),
    updated_before: AwareTimestamp | None = Query(default=None),
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
        created_after: Optional inclusive created-at lower bound.
        created_before: Optional inclusive created-at upper bound.
        updated_after: Optional inclusive updated-at lower bound.
        updated_before: Optional inclusive updated-at upper bound.
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
        created_after=created_after,
        created_before=created_before,
        updated_after=updated_after,
        updated_before=updated_before,
        include_archived=include_archived,
    )
    response = ContextListResponse.model_validate(
        {"items": [context_payload(item) for item in items], "total": total}
    )
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


@router.delete(
    "/{context_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    description="Hard delete one Context Vault entry and its retrieval/audit rows.",
    summary="Delete context",
)
@router_exception_status(CONTEXT_ROUTE_EXCEPTION_MAPPING)
@inject
async def delete_context(
    context_id: str,
    service: ContextService = Depends(
        Provide[ApplicationContainer.memory.context_service]
    ),
) -> Response:
    """Hard delete one context.

    Args:
        context_id: Context identifier.
        service: Context application service.

    Returns:
        Empty HTTP 204 response.
    """
    await service.delete(context_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/{context_id}/archive",
    response_model=ContextResponse,
    status_code=status.HTTP_200_OK,
    description="Archive one context without hard deleting its durable row.",
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
