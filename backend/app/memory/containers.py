"""Dependency-injector container for memory bounded context."""

from __future__ import annotations

from app.memory.application.context_service import ContextService
from app.memory.application.memory_compact_service import MemoryCompactService
from app.memory.infrastructure.repositories.context_repository import (
    SqlAlchemyContextRepository,
)
from app.memory.infrastructure.repositories.memory_compact_repository import (
    ObsidianMemoryCompactRepository,
)
from app.platform.config.app_config import AppConfig
from app.retrieval.application.embedding_factory import create_embedding_provider
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
    )
    memory_compact_service = providers.Factory(
        MemoryCompactService,
        repository=memory_compact_repo,
    )
