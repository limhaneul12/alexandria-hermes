"""Dependency-injector container for memory bounded context."""

from __future__ import annotations

from app.memory.application.context_service import ContextService
from app.memory.application.integration.obsidian_canonical_context_gateway import (
    ObsidianCanonicalContextGateway,
)
from app.memory.application.memory_compact_service import MemoryCompactService
from app.memory.application.retrieval.embedding_factory import create_embedding_provider
from app.memory.infrastructure.repositories.context_repository import (
    SqlAlchemyContextRepository,
)
from app.memory.infrastructure.repositories.contexts.obsidian_search_source import (
    SqlAlchemyObsidianContextSearchSource,
)
from app.memory.infrastructure.repositories.memory_compact_repository import (
    ObsidianMemoryCompactRepository,
)
from app.obsidian.application.service.obsidian_service import ObsidianService
from app.obsidian.infrastructure.obsidian_vault_config_store import (
    ObsidianVaultConfigStore,
)
from app.obsidian.infrastructure.repositories.obsidian_index_repository import (
    SqlAlchemyObsidianIndexRepository,
)
from app.platform.config.app_config import AppConfig
from dependency_injector import containers, providers
from sqlalchemy.ext.asyncio import AsyncSession


class MemoryContainer(containers.DeclarativeContainer):
    """Container for scoped memory/context-vault components."""

    db_session = providers.Dependency(instance_of=AsyncSession)
    app_config = providers.Dependency(instance_of=AppConfig)
    embedding_provider = providers.Factory(
        create_embedding_provider,
        vector_enabled=app_config.provided.rag_vector_enabled,
        provider_name=app_config.provided.rag_embedding_provider,
        model_name=app_config.provided.rag_embedding_model,
        dimensions=app_config.provided.rag_embedding_dimensions,
        cache_dir=app_config.provided.rag_embedding_cache_dir,
    )
    context_repo = providers.Factory(SqlAlchemyContextRepository, session=db_session)
    obsidian_context_search_source = providers.Factory(
        SqlAlchemyObsidianContextSearchSource,
        session=db_session,
    )
    obsidian_vault_config_store = providers.Singleton(
        ObsidianVaultConfigStore,
        default_vault_path=app_config.provided.obsidian_vault_path,
        default_alexandria_root=app_config.provided.alexandria_obsidian_root,
        config_path=app_config.provided.obsidian_vault_config_path,
    )
    obsidian_index_repo = providers.Factory(
        SqlAlchemyObsidianIndexRepository,
        session=db_session,
    )
    obsidian_service = providers.Factory(
        ObsidianService,
        repository=obsidian_index_repo,
        vault_config_store=obsidian_vault_config_store,
    )
    canonical_context_gateway = providers.Factory(
        ObsidianCanonicalContextGateway,
        service=obsidian_service,
    )
    memory_compact_repo = providers.Factory(
        ObsidianMemoryCompactRepository,
        vault_path=app_config.provided.obsidian_vault_path,
        relative_dir=app_config.provided.memory_compact_note_dir,
    )
    context_service = providers.Factory(
        ContextService,
        repository=context_repo,
        embedding_provider=embedding_provider,
        vector_retrieval_enabled=app_config.provided.rag_vector_enabled,
        extra_search_sources=providers.List(obsidian_context_search_source),
        canonical_context_repository=canonical_context_gateway,
    )
    memory_compact_service = providers.Factory(
        MemoryCompactService,
        repository=memory_compact_repo,
    )
