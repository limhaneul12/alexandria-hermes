"""Routes for Obsidian-backed Alexandria vault operations."""

from __future__ import annotations

from app.container import ApplicationContainer
from app.obsidian.application.obsidian_service import ObsidianService
from app.obsidian.interface.schemas.obsidian.obsidian_schema import (
    ObsidianLibrarianAskRequest,
    ObsidianLibrarianAskResponse,
    ObsidianNoteResponse,
    ObsidianReindexResponse,
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
