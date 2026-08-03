"""Note, search, and graph routes for Obsidian-backed Alexandria storage."""

from __future__ import annotations

from app.container import ApplicationContainer
from app.obsidian.application.graph.obsidian_graph_service import ObsidianGraphService
from app.obsidian.application.service.obsidian_service import ObsidianService
from app.obsidian.interface.schemas.obsidian.obsidian_schema import (
    ObsidianNoteResponse,
    ObsidianRelatedNoteResponse,
    ObsidianRelatedNotesResponse,
    ObsidianSaveNoteRequest,
    ObsidianSearchHitResponse,
    ObsidianSearchRequest,
    ObsidianSearchResponse,
)
from app.shared.exceptions.exception_decorators import router_exception_status
from app.shared.exceptions.route_exceptions import (
    OBSIDIAN_ROUTE_EXCEPTION_MAPPING,
    OBSIDIAN_SAVE_ROUTE_EXCEPTION_MAPPING,
)
from dependency_injector.wiring import Provide, inject
from fastapi import APIRouter, Depends, Query, status

router = APIRouter()


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
    hits = await service.search(request.to_query(), refresh=request.refresh)
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
@router_exception_status(OBSIDIAN_SAVE_ROUTE_EXCEPTION_MAPPING)
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
