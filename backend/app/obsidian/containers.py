"""Dependency-injector container for Obsidian bounded context."""

from __future__ import annotations

from collections.abc import Awaitable, Callable

from app.memory.application.context_service import ContextService
from app.obsidian.application.graph.obsidian_graph_service import ObsidianGraphService
from app.obsidian.application.librarian.obsidian_librarian_job_service import (
    ObsidianLibrarianJobService,
)
from app.obsidian.application.librarian.obsidian_librarian_workflow_service import (
    ObsidianLibrarianWorkflowService,
)
from app.obsidian.application.service.obsidian_service import ObsidianService
from app.obsidian.infrastructure.obsidian_vault_config_store import (
    ObsidianVaultConfigStore,
)
from app.obsidian.infrastructure.repositories.obsidian_index_repository import (
    SqlAlchemyObsidianIndexRepository,
)
from app.obsidian.infrastructure.repositories.obsidian_workflow_repository import (
    SqlAlchemyObsidianWorkflowRepository,
)
from app.platform.config.app_config import AppConfig
from app.shared.infrastructure.database import Database
from dependency_injector import containers, providers
from sqlalchemy.ext.asyncio import AsyncSession


def _build_context_reindex_hook(
    context_service: ContextService | None,
) -> Callable[[], Awaitable[None]] | None:
    """Build an async hook that backfills context embeddings after vault reindex."""
    if context_service is None:
        return None

    async def _hook() -> None:
        await context_service.reindex_embeddings(limit=1000, force=True)

    return _hook


class ObsidianContainer(containers.DeclarativeContainer):
    """Container for Obsidian vault and index services."""

    db_session = providers.Dependency(instance_of=AsyncSession)
    database = providers.Dependency(instance_of=Database)
    app_config = providers.Dependency(instance_of=AppConfig)
    librarian_delegate_service = providers.Dependency(default=None)
    memory_context_service = providers.Dependency(
        instance_of=ContextService,
        default=None,
    )
    index_repo = providers.Factory(
        SqlAlchemyObsidianIndexRepository, session=db_session
    )
    vault_config_store = providers.Singleton(
        ObsidianVaultConfigStore,
        default_vault_path=app_config.provided.obsidian_vault_path,
        default_alexandria_root=app_config.provided.alexandria_obsidian_root,
        config_path=app_config.provided.obsidian_vault_config_path,
    )
    obsidian_service = providers.Factory(
        ObsidianService,
        repository=index_repo,
        vault_config_store=vault_config_store,
        delegate_service=librarian_delegate_service,
        context_reindex_hook=providers.Factory(
            _build_context_reindex_hook,
            context_service=memory_context_service,
        ),
    )
    graph_service = providers.Factory(
        ObsidianGraphService,
        repository=index_repo,
        obsidian_service=obsidian_service,
    )
    job_service = providers.Singleton(
        ObsidianLibrarianJobService,
        database=database,
        vault_config_store=vault_config_store,
        delegate_service=librarian_delegate_service,
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
