"""Dependency-injector container for Obsidian bounded context."""

from __future__ import annotations

from app.obsidian.application.obsidian_graph_service import ObsidianGraphService
from app.obsidian.application.obsidian_librarian_workflow_service import (
    ObsidianLibrarianWorkflowService,
)
from app.obsidian.application.obsidian_service import ObsidianService
from app.obsidian.infrastructure.repositories.obsidian_index_repository import (
    SqlAlchemyObsidianIndexRepository,
)
from app.obsidian.infrastructure.repositories.obsidian_workflow_repository import (
    SqlAlchemyObsidianWorkflowRepository,
)
from app.platform.config.app_config import AppConfig
from dependency_injector import containers, providers
from sqlalchemy.ext.asyncio import AsyncSession


class ObsidianContainer(containers.DeclarativeContainer):
    """Container for Obsidian vault and index services."""

    db_session = providers.Dependency(instance_of=AsyncSession)
    app_config = providers.Dependency(instance_of=AppConfig)
    librarian_delegate_service = providers.Dependency(default=None)
    index_repo = providers.Factory(
        SqlAlchemyObsidianIndexRepository, session=db_session
    )
    obsidian_service = providers.Factory(
        ObsidianService,
        repository=index_repo,
        vault_path=app_config.provided.obsidian_vault_path,
        alexandria_root=app_config.provided.alexandria_obsidian_root,
    )
    graph_service = providers.Factory(
        ObsidianGraphService,
        repository=index_repo,
        obsidian_service=obsidian_service,
    )
    workflow_repo = providers.Factory(
        SqlAlchemyObsidianWorkflowRepository, session=db_session
    )
    workflow_service = providers.Factory(
        ObsidianLibrarianWorkflowService.from_services,
        workflow_repository=workflow_repo,
        obsidian_service=obsidian_service,
        checkpoint_path=app_config.provided.obsidian_librarian_langgraph_checkpoint_path,
        delegate_service=librarian_delegate_service,
    )
