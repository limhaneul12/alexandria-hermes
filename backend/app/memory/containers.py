"""Dependency-injector container for memory bounded context."""

from __future__ import annotations

from app.memory.application.context_service import ContextService
from app.memory.infrastructure.repositories.context_repository import (
    SqlAlchemyContextRepository,
)
from dependency_injector import containers, providers
from sqlalchemy.ext.asyncio import AsyncSession


class MemoryContainer(containers.DeclarativeContainer):
    """Container for scoped memory/context-vault components."""

    db_session = providers.Dependency(instance_of=AsyncSession)
    context_repo = providers.Factory(SqlAlchemyContextRepository, session=db_session)
    context_service = providers.Factory(ContextService, repository=context_repo)
