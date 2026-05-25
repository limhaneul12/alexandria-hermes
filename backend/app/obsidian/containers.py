"""Dependency-injector container for Obsidian bounded context."""

from __future__ import annotations

from app.obsidian.application.obsidian_service import ObsidianService
from app.obsidian.infrastructure.repositories.obsidian_index_repository import (
    SqlAlchemyObsidianIndexRepository,
)
from app.platform.config.app_config import AppConfig
from dependency_injector import containers, providers
from sqlalchemy.ext.asyncio import AsyncSession


class ObsidianContainer(containers.DeclarativeContainer):
    """Container for Obsidian vault and index services."""

    db_session = providers.Dependency(instance_of=AsyncSession)
    app_config = providers.Dependency(instance_of=AppConfig)
    index_repo = providers.Factory(
        SqlAlchemyObsidianIndexRepository, session=db_session
    )
    obsidian_service = providers.Factory(
        ObsidianService,
        repository=index_repo,
        vault_path=app_config.provided.obsidian_vault_path,
        alexandria_root=app_config.provided.alexandria_obsidian_root,
    )
