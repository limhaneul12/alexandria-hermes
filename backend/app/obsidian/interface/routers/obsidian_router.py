"""Routes for Obsidian-backed Alexandria vault operations."""

from __future__ import annotations

from app.container import ApplicationContainer
from app.obsidian.application.obsidian_graph_service import ObsidianGraphService
from app.obsidian.application.obsidian_librarian_workflow_service import (
    ObsidianLibrarianWorkflowService,
)
from app.obsidian.application.obsidian_service import ObsidianService
from app.obsidian.domain.contracts.obsidian_contracts import (
    ObsidianLibrarianWorkflowResume,
)
from app.obsidian.interface.schemas.obsidian.obsidian_librarian_workflow_schema import (
    ObsidianLibrarianAskRequest,
    ObsidianLibrarianAskResponse,
    ObsidianLibrarianWorkflowResponse,
    ObsidianLibrarianWorkflowResumeRequest,
)
from app.obsidian.interface.schemas.obsidian.obsidian_schema import (
    ObsidianNoteResponse,
    ObsidianReindexResponse,
    ObsidianRelatedNoteResponse,
    ObsidianRelatedNotesResponse,
    ObsidianSaveNoteRequest,
    ObsidianSearchHitResponse,
    ObsidianSearchRequest,
    ObsidianSearchResponse,
    ObsidianStatusResponse,
)
from app.shared.exceptions.exception_decorators import router_exception_status
from app.shared.exceptions.route_exceptions import OBSIDIAN_ROUTE_EXCEPTION_MAPPING
from dependency_injector.wiring import Provide, inject
from fastapi import APIRouter, Depends, Query, status

router = APIRouter(prefix="/obsidian", tags=["obsidian"])


@router.get(
    "/status",
    response_model=ObsidianStatusResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Obsidian index status",
    description="Return Obsidian vault and Alexandria index status.",
)
@router_exception_status(OBSIDIAN_ROUTE_EXCEPTION_MAPPING)
@inject
async def obsidian_status(
    service: ObsidianService = Depends(
        Provide[ApplicationContainer.obsidian.obsidian_service]
    ),
) -> ObsidianStatusResponse:
    """Return Obsidian vault/index status.

    Args:
        service: Obsidian application service.

    Returns:
        Current vault/index status response.
    """
    result = await service.status()
    return ObsidianStatusResponse.from_entity(result)


@router.post(
    "/init",
    response_model=ObsidianNoteResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Initialize Obsidian vault",
    description="Create Alexandria folders and START_HERE note in the Obsidian vault.",
)
@router_exception_status(OBSIDIAN_ROUTE_EXCEPTION_MAPPING)
@inject
async def initialize_obsidian_vault(
    service: ObsidianService = Depends(
        Provide[ApplicationContainer.obsidian.obsidian_service]
    ),
) -> ObsidianNoteResponse:
    """Initialize the managed Obsidian vault layout.

    Args:
        service: Obsidian application service.

    Returns:
        START_HERE note response.
    """
    note = await service.initialize_vault()
    return ObsidianNoteResponse.from_entity(note)


@router.post(
    "/index/rebuild",
    response_model=ObsidianReindexResponse,
    status_code=status.HTTP_200_OK,
    summary="Reindex Obsidian vault",
    description="Scan Alexandria Markdown notes and rebuild the SQLite search cache.",
)
@router_exception_status(OBSIDIAN_ROUTE_EXCEPTION_MAPPING)
@inject
async def reindex_obsidian_vault(
    service: ObsidianService = Depends(
        Provide[ApplicationContainer.obsidian.obsidian_service]
    ),
) -> ObsidianReindexResponse:
    """Rebuild the Obsidian index cache.

    Args:
        service: Obsidian application service.

    Returns:
        Reindex summary response.
    """
    result = await service.reindex()
    return ObsidianReindexResponse.from_entity(result)


@router.post(
    "/search",
    response_model=ObsidianSearchResponse,
    status_code=status.HTTP_200_OK,
    summary="Search Obsidian notes",
    description="Search Alexandria-managed Obsidian Markdown notes.",
)
@router_exception_status(OBSIDIAN_ROUTE_EXCEPTION_MAPPING)
@inject
async def search_obsidian_notes(
    request: ObsidianSearchRequest,
    service: ObsidianService = Depends(
        Provide[ApplicationContainer.obsidian.obsidian_service]
    ),
) -> ObsidianSearchResponse:
    """Search indexed Obsidian notes.

    Args:
        request: Search request body.
        service: Obsidian application service.

    Returns:
        Search result response.
    """
    hits = await service.search(request.to_query())
    items = [ObsidianSearchHitResponse.from_entity(hit) for hit in hits]
    return ObsidianSearchResponse(items=items, total=len(items))


@router.get(
    "/notes/by-path/related",
    response_model=ObsidianRelatedNotesResponse,
    status_code=status.HTTP_200_OK,
    summary="Read related Obsidian notes by path",
    description="Return graph-related notes for one vault-relative Markdown path.",
)
@router_exception_status(OBSIDIAN_ROUTE_EXCEPTION_MAPPING)
@inject
async def related_obsidian_notes_by_path(
    path: str = Query(min_length=1),
    limit: int = Query(default=10, ge=1, le=50),
    service: ObsidianGraphService = Depends(
        Provide[ApplicationContainer.obsidian.graph_service]
    ),
) -> ObsidianRelatedNotesResponse:
    """Return related notes for one path.

    Args:
        path: Vault-relative Markdown path.
        limit: Maximum related-note count.
        service: Obsidian graph service.

    Returns:
        Related notes response.
    """
    items = await service.related_notes_by_path(path, limit=limit)
    responses = [ObsidianRelatedNoteResponse.from_entity(item) for item in items]
    return ObsidianRelatedNotesResponse(items=responses, total=len(responses))


@router.get(
    "/notes/by-path",
    response_model=ObsidianNoteResponse,
    status_code=status.HTTP_200_OK,
    summary="Read Obsidian note by path",
    description="Read one Alexandria-managed note by vault-relative path.",
)
@router_exception_status(OBSIDIAN_ROUTE_EXCEPTION_MAPPING)
@inject
async def read_obsidian_note_by_path(
    path: str = Query(min_length=1),
    service: ObsidianService = Depends(
        Provide[ApplicationContainer.obsidian.obsidian_service]
    ),
) -> ObsidianNoteResponse:
    """Read one Obsidian note by path.

    Args:
        path: Vault-relative path.
        service: Obsidian application service.

    Returns:
        Note response.
    """
    note = await service.read_note_by_path(path)
    return ObsidianNoteResponse.from_entity(note)


@router.get(
    "/notes/{note_id}/related",
    response_model=ObsidianRelatedNotesResponse,
    status_code=status.HTTP_200_OK,
    summary="Read related Obsidian notes",
    description="Return graph-related notes for one stable note id.",
)
@router_exception_status(OBSIDIAN_ROUTE_EXCEPTION_MAPPING)
@inject
async def related_obsidian_notes(
    note_id: str,
    limit: int = Query(default=10, ge=1, le=50),
    service: ObsidianGraphService = Depends(
        Provide[ApplicationContainer.obsidian.graph_service]
    ),
) -> ObsidianRelatedNotesResponse:
    """Return related notes for one stable note id.

    Args:
        note_id: Stable note id.
        limit: Maximum related-note count.
        service: Obsidian graph service.

    Returns:
        Related notes response.
    """
    items = await service.related_notes(note_id, limit=limit)
    responses = [ObsidianRelatedNoteResponse.from_entity(item) for item in items]
    return ObsidianRelatedNotesResponse(items=responses, total=len(responses))


@router.get(
    "/notes/{note_id}",
    response_model=ObsidianNoteResponse,
    status_code=status.HTTP_200_OK,
    summary="Read Obsidian note",
    description="Read one Alexandria-managed note by stable id.",
)
@router_exception_status(OBSIDIAN_ROUTE_EXCEPTION_MAPPING)
@inject
async def read_obsidian_note(
    note_id: str,
    service: ObsidianService = Depends(
        Provide[ApplicationContainer.obsidian.obsidian_service]
    ),
) -> ObsidianNoteResponse:
    """Read one Obsidian note by id.

    Args:
        note_id: Stable note id.
        service: Obsidian application service.

    Returns:
        Note response.
    """
    note = await service.read_note(note_id)
    return ObsidianNoteResponse.from_entity(note)


@router.post(
    "/notes",
    response_model=ObsidianNoteResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Save Obsidian note",
    description="Create or replace one Alexandria-managed Markdown note.",
)
@router_exception_status(OBSIDIAN_ROUTE_EXCEPTION_MAPPING)
@inject
async def save_obsidian_note(
    request: ObsidianSaveNoteRequest,
    service: ObsidianService = Depends(
        Provide[ApplicationContainer.obsidian.obsidian_service]
    ),
) -> ObsidianNoteResponse:
    """Save one Obsidian Markdown note.

    Args:
        request: Save request body.
        service: Obsidian application service.

    Returns:
        Saved note response.
    """
    note = await service.save_note(request.to_command())
    return ObsidianNoteResponse.from_entity(note)


@router.post(
    "/librarian/ask",
    response_model=ObsidianLibrarianAskResponse,
    status_code=status.HTTP_200_OK,
    summary="Ask Obsidian librarian",
    description="Ask the Alexandria librarian using active Obsidian note context.",
)
@router_exception_status(OBSIDIAN_ROUTE_EXCEPTION_MAPPING)
@inject
async def ask_obsidian_librarian(
    request: ObsidianLibrarianAskRequest,
    service: ObsidianService = Depends(
        Provide[ApplicationContainer.obsidian.obsidian_service]
    ),
) -> ObsidianLibrarianAskResponse:
    """Ask the Obsidian-aware librarian adapter.

    Args:
        request: Librarian ask request body.
        service: Obsidian application service.

    Returns:
        Librarian response.
    """
    payload = await service.ask_librarian(request.to_command())
    response = ObsidianLibrarianAskResponse.model_validate(payload)
    return response


@router.post(
    "/librarian/workflows",
    response_model=ObsidianLibrarianWorkflowResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Start Obsidian librarian workflow",
    description="Start a resumable local librarian workflow and pause for approval.",
)
@router_exception_status(OBSIDIAN_ROUTE_EXCEPTION_MAPPING)
@inject
async def start_obsidian_librarian_workflow(
    request: ObsidianLibrarianAskRequest,
    service: ObsidianLibrarianWorkflowService = Depends(
        Provide[ApplicationContainer.obsidian.workflow_service]
    ),
) -> ObsidianLibrarianWorkflowResponse:
    """Start a resumable librarian workflow.

    Args:
        request: Librarian workflow start request.
        service: Workflow application service.

    Returns:
        Workflow checkpoint response.
    """
    workflow = await service.start_workflow(request.to_command())
    return ObsidianLibrarianWorkflowResponse.from_entity(workflow)


@router.get(
    "/librarian/workflows/{thread_id}",
    response_model=ObsidianLibrarianWorkflowResponse,
    status_code=status.HTTP_200_OK,
    summary="Read Obsidian librarian workflow",
    description="Read a persisted librarian workflow checkpoint.",
)
@router_exception_status(OBSIDIAN_ROUTE_EXCEPTION_MAPPING)
@inject
async def get_obsidian_librarian_workflow(
    thread_id: str,
    service: ObsidianLibrarianWorkflowService = Depends(
        Provide[ApplicationContainer.obsidian.workflow_service]
    ),
) -> ObsidianLibrarianWorkflowResponse:
    """Read a persisted librarian workflow.

    Args:
        thread_id: Workflow thread id.
        service: Workflow application service.

    Returns:
        Workflow checkpoint response.
    """
    workflow = await service.get_workflow(thread_id)
    return ObsidianLibrarianWorkflowResponse.from_entity(workflow)


@router.post(
    "/librarian/workflows/{thread_id}/resume",
    response_model=ObsidianLibrarianWorkflowResponse,
    status_code=status.HTTP_200_OK,
    summary="Resume Obsidian librarian workflow",
    description="Apply approved workflow actions and persist a completed checkpoint.",
)
@router_exception_status(OBSIDIAN_ROUTE_EXCEPTION_MAPPING)
@inject
async def resume_obsidian_librarian_workflow(
    thread_id: str,
    request: ObsidianLibrarianWorkflowResumeRequest,
    service: ObsidianLibrarianWorkflowService = Depends(
        Provide[ApplicationContainer.obsidian.workflow_service]
    ),
) -> ObsidianLibrarianWorkflowResponse:
    """Resume a persisted librarian workflow.

    Args:
        thread_id: Workflow thread id.
        request: Approved actions request.
        service: Workflow application service.

    Returns:
        Workflow checkpoint response.
    """
    workflow = await service.resume_workflow(
        ObsidianLibrarianWorkflowResume(
            thread_id=thread_id, approved_actions=request.approved_actions
        )
    )
    return ObsidianLibrarianWorkflowResponse.from_entity(workflow)


@router.post(
    "/librarian/workflows/{thread_id}/cancel",
    response_model=ObsidianLibrarianWorkflowResponse,
    status_code=status.HTTP_200_OK,
    summary="Cancel Obsidian librarian workflow",
    description="Cancel a persisted librarian workflow without writing notes.",
)
@router_exception_status(OBSIDIAN_ROUTE_EXCEPTION_MAPPING)
@inject
async def cancel_obsidian_librarian_workflow(
    thread_id: str,
    service: ObsidianLibrarianWorkflowService = Depends(
        Provide[ApplicationContainer.obsidian.workflow_service]
    ),
) -> ObsidianLibrarianWorkflowResponse:
    """Cancel a persisted librarian workflow.

    Args:
        thread_id: Workflow thread id.
        service: Workflow application service.

    Returns:
        Workflow checkpoint response.
    """
    workflow = await service.cancel_workflow(thread_id)
    return ObsidianLibrarianWorkflowResponse.from_entity(workflow)
