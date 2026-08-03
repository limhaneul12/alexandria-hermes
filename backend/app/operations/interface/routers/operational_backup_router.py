"""Local-only operational backup and non-destructive restore-drill routes."""

from __future__ import annotations

from dependency_injector.wiring import Provide, inject
from fastapi import APIRouter, Depends, HTTPException, Request, status

from app.container import ApplicationContainer
from app.obsidian.application.service.obsidian_service import ObsidianService
from app.operations.application.operational_state_backup_service import (
    OperationalStateBackupService,
)
from app.operations.application.operational_state_restore_service import (
    OperationalStateRestoreService,
)
from app.operations.interface.schemas.operations.operational_backup_schema import (
    OperationalBackupResponse,
    OperationalRestoreDrillResponse,
)
from app.platform.config.app_config import AppConfig
from app.shared.exceptions.exception_decorators import router_exception_status
from app.shared.exceptions.route_exceptions import OPERATIONS_ROUTE_EXCEPTION_MAPPING
from app.shared.infrastructure.database import Database

router = APIRouter(prefix="/operations", tags=["operations"])
_LOCAL_HOSTS = frozenset({"127.0.0.1", "localhost", "::1", "testserver"})


@router.post(
    "/backups",
    response_model=OperationalBackupResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a local operational backup",
    description=(
        "Snapshot the canonical Vault, operational SQLite state, and optional "
        "Librarian checkpoint into a hash-manifested local backup."
    ),
)
@router_exception_status(OPERATIONS_ROUTE_EXCEPTION_MAPPING)
@inject
async def create_operational_backup(
    request: Request,
    database: Database = Depends(Provide[ApplicationContainer.database]),
    obsidian_service: ObsidianService = Depends(
        Provide[ApplicationContainer.obsidian.obsidian_service]
    ),
) -> OperationalBackupResponse:
    """Create one verified backup without returning secret contents.

    Args:
        request: Active local FastAPI request.
        database: Shared operational database coordinator.
        obsidian_service: Canonical Vault status boundary.

    Returns:
        Published backup evidence.
    """
    config = _local_config(request)
    database_path = database.sqlite_path
    if database_path is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Operational backup currently requires local SQLite",
        )
    vault = obsidian_service.vault_location()
    service = OperationalStateBackupService(
        backup_root=config.operational_backup_root,
        operational_database_path=database_path,
        librarian_checkpoint_path=(config.obsidian_librarian_langgraph_checkpoint_path),
        retention_count=config.operational_backup_retention_count,
    )
    result = await service.create(
        vault_path=vault.vault_path,
        alexandria_root=vault.alexandria_root,
    )
    return OperationalBackupResponse.from_entity(result)


@router.post(
    "/backups/{backup_id}/restore-drill",
    response_model=OperationalRestoreDrillResponse,
    status_code=status.HTTP_200_OK,
    summary="Run a non-destructive operational restore drill",
    description=(
        "Verify every manifest hash and restore into an isolated drill directory. "
        "Live Vault and databases are never overwritten."
    ),
)
@router_exception_status(OPERATIONS_ROUTE_EXCEPTION_MAPPING)
@inject
async def drill_operational_restore(
    backup_id: str,
    request: Request,
    configured_app: AppConfig = Depends(Provide[ApplicationContainer.app_config]),
) -> OperationalRestoreDrillResponse:
    """Run an isolated restore and SQLite integrity verification.

    Args:
        backup_id: Published backup identifier.
        request: Active local FastAPI request.
        configured_app: Dependency-injected configuration fallback.

    Returns:
        Hash and SQLite verification evidence.
    """
    config = _local_config(request, configured_app)
    result = await OperationalStateRestoreService(
        backup_root=config.operational_backup_root
    ).drill(backup_id=backup_id)
    return OperationalRestoreDrillResponse.from_entity(result)


def _local_config(request: Request, fallback: AppConfig | None = None) -> AppConfig:
    config = getattr(request.app.state, "app_config", fallback or AppConfig())
    if request.url.hostname not in _LOCAL_HOSTS or config.app_env != "local":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Operational backup actions are local-environment only",
        )
    return config
