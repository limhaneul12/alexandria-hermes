"""Vault and index lifecycle routes for Obsidian-backed Alexandria storage."""

from __future__ import annotations

from app.container import ApplicationContainer
from app.obsidian.application.service.obsidian_service import ObsidianService
from app.obsidian.interface.schemas.obsidian.obsidian_schema import (
    ObsidianNoteResponse,
    ObsidianReindexResponse,
    ObsidianStatusResponse,
)
from app.shared.exceptions.exception_decorators import router_exception_status
from app.shared.exceptions.route_exceptions import (
    OBSIDIAN_ROUTE_EXCEPTION_MAPPING,
)
from dependency_injector.wiring import Provide, inject
from fastapi import APIRouter, Depends, status

router = APIRouter()


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
