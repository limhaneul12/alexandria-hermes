"""Routes for Obsidian backend runtime settings."""

from __future__ import annotations

from app.container import ApplicationContainer
from app.obsidian.application.service.obsidian_service import ObsidianService
from app.obsidian.interface.schemas.obsidian.obsidian_schema import (
    ObsidianStatusResponse,
)
from app.obsidian.interface.schemas.obsidian.obsidian_settings_schema import (
    ObsidianVaultSettingsUpdateRequest,
)
from app.shared.exceptions.exception_decorators import router_exception_status
from app.shared.exceptions.route_exceptions import OBSIDIAN_ROUTE_EXCEPTION_MAPPING
from dependency_injector.wiring import Provide, inject
from fastapi import APIRouter, Depends, status

router = APIRouter(
    prefix="/obsidian/settings",
    tags=["obsidian"],
)


@router.put(
    "/vault",
    response_model=ObsidianStatusResponse,
    status_code=status.HTTP_200_OK,
    summary="Configure Obsidian vault destination",
    description=(
        "Persist the backend vault path/root used for future Alexandria "
        "Obsidian writes. Intended for the local Obsidian plugin settings pane."
    ),
)
@router_exception_status(OBSIDIAN_ROUTE_EXCEPTION_MAPPING)
@inject
async def configure_obsidian_vault_settings(
    request: ObsidianVaultSettingsUpdateRequest,
    service: ObsidianService = Depends(
        Provide[ApplicationContainer.obsidian.obsidian_service]
    ),
) -> ObsidianStatusResponse:
    """Apply runtime Obsidian vault settings.

    Args:
        request: Vault destination settings from an authorized local operator.
        service: Obsidian application service.

    Returns:
        Current vault/index status response.
    """
    result = await service.configure_vault_settings(request.to_command())
    return ObsidianStatusResponse.from_entity(result)
