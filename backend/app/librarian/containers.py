"""Dependency-injector container for librarian bounded context."""

from __future__ import annotations

from app.connections.domain.repositories.librarian_repository import (
    ILibrarianProviderRepository,
    IProviderSecretRepository,
)
from app.librarian.application.agent_service import AgentService
from app.librarian.application.hermes_collaboration_service import (
    HermesCollaborationService,
)
from app.librarian.infrastructure.repositories.agent_repository import (
    SqlAlchemyAgentRepository,
)
from dependency_injector import containers, providers
from sqlalchemy.ext.asyncio import AsyncSession


class LibrarianContainer(containers.DeclarativeContainer):
    """Container for librarian profiles, routing, and collaboration."""

    db_session = providers.Dependency(instance_of=AsyncSession)
    agent_repo = providers.Factory(SqlAlchemyAgentRepository, session=db_session)
    librarian_provider_repo = providers.Dependency(
        instance_of=ILibrarianProviderRepository
    )
    provider_secret_repo = providers.Dependency(instance_of=IProviderSecretRepository)
    agent_service = providers.Factory(
        AgentService,
        repository=agent_repo,
        provider_repo=librarian_provider_repo,
        secret_repo=provider_secret_repo,
    )
    hermes_collaboration_service = providers.Factory(
        HermesCollaborationService,
        provider_repo=librarian_provider_repo,
        agent_repo=agent_repo,
        secret_repo=provider_secret_repo,
    )
