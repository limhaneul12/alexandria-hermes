"""FastAPI dependency helpers for database-scoped repositories and services."""

from __future__ import annotations

from collections.abc import AsyncIterator

from app.container import ApplicationContainer
from app.library.application.agent_service import AgentService
from app.library.application.category_service import CategoryService
from app.library.application.item_service import ItemService
from app.library.application.knowledge_service import KnowledgeService
from app.library.application.librarian_service import LibrarianService
from app.library.application.skill_service import SkillService
from app.library.application.usage_service import UsageService
from app.library.application.workflow_service import WorkflowService
from app.library.domain.repositories.agent_repository import AgentRepository
from app.library.domain.repositories.category_repository import CategoryRepository
from app.library.domain.repositories.item_repository import ItemRepository
from app.library.domain.repositories.librarian_repository import (
    LibrarianProviderRepository,
)
from app.library.domain.repositories.usage_repository import UsageRepository
from app.library.infrastructure.repositories import ProviderSecretRepository
from fastapi import Depends
from fastapi.requests import Request
from sqlalchemy.ext.asyncio import AsyncSession


def _container_from_request(request: Request) -> ApplicationContainer:
    """Return shared container from request state.

    Args:
        request: Incoming HTTP request.

    Return:
        Application container bound to the current app instance.
    """
    return request.app.state.container


async def get_db_session(request: Request) -> AsyncIterator[AsyncSession]:
    """Yield a request-scoped async session and commit successful transactions.

    Args:
        request: Active request object.

    Return:
        AsyncSession instance for repositories.

    Raises:
        Exception: Re-raises unexpected errors after rollback.
    """
    container = _container_from_request(request=request)
    session_factory = await container.db_session()
    session = session_factory()
    try:
        yield session
        await session.commit()
    except Exception as error:
        await session.rollback()
        raise error
    finally:
        await session.close()


def get_item_repository(
    request: Request,
    session: AsyncSession = Depends(get_db_session),
) -> ItemRepository:
    """Build request-scoped item repository.

    Args:
        request: Incoming HTTP request.
        session: Async DB session.

    Return:
        Item repository instance.
    """
    container = _container_from_request(request=request).library()
    return container.item_repo(session=session)


def get_usage_repository(
    request: Request,
    session: AsyncSession = Depends(get_db_session),
) -> UsageRepository:
    """Build request-scoped usage repository.

    Args:
        request: Incoming HTTP request.
        session: Async DB session.

    Return:
        Usage repository instance.
    """
    container = _container_from_request(request=request).library()
    return container.usage_repo(session=session)


def get_category_repository(
    request: Request,
    session: AsyncSession = Depends(get_db_session),
) -> CategoryRepository:
    """Build request-scoped category repository.

    Args:
        request: Incoming HTTP request.
        session: Async DB session.

    Return:
        Category repository instance.
    """
    container = _container_from_request(request=request).library()
    return container.category_repo(session=session)


def get_agent_repository(
    request: Request,
    session: AsyncSession = Depends(get_db_session),
) -> AgentRepository:
    """Build request-scoped agent repository.

    Args:
        request: Incoming HTTP request.
        session: Async DB session.

    Return:
        Agent repository instance.
    """
    container = _container_from_request(request=request).library()
    return container.agent_repo(session=session)


def get_librarian_repository(
    request: Request,
    session: AsyncSession = Depends(get_db_session),
) -> LibrarianProviderRepository:
    """Build request-scoped librarian repository.

    Args:
        request: Incoming HTTP request.
        session: Async DB session.

    Return:
        Librarian provider repository instance.
    """
    container = _container_from_request(request=request).library()
    return container.librarian_provider_repo(session=session)


def get_secret_repository(
    request: Request,
    session: AsyncSession = Depends(get_db_session),
) -> ProviderSecretRepository:
    """Build request-scoped secret repository.

    Args:
        request: Incoming HTTP request.
        session: Async DB session.

    Return:
        Provider secret repository instance.
    """
    container = _container_from_request(request=request).library()
    return container.provider_secret_repo(session=session)


def get_item_service(
    request: Request,
    item_repo: ItemRepository = Depends(get_item_repository),
) -> ItemService:
    """Build request-scoped item service.

    Args:
        request: Incoming HTTP request.
        item_repo: Item repository from dependency chain.

    Return:
        Item service instance.
    """
    container = _container_from_request(request=request)
    return container.library().item_service(item_repo=item_repo)


def get_category_service(
    request: Request,
    category_repo: CategoryRepository = Depends(get_category_repository),
) -> CategoryService:
    """Build request-scoped category service.

    Args:
        request: Incoming HTTP request.
        category_repo: Category repository from dependency chain.

    Return:
        Category service instance.
    """
    container = _container_from_request(request=request)
    return container.library().category_service(category_repo=category_repo)


def get_skill_service(
    request: Request,
    item_service: ItemService = Depends(get_item_service),
) -> SkillService:
    """Build request-scoped skill service.

    Args:
        request: Incoming HTTP request.
        item_service: Item service from dependency chain.

    Return:
        Skill service instance.
    """
    container = _container_from_request(request=request)
    return container.library().skill_service(item_service=item_service)


def get_workflow_service(
    request: Request,
    item_service: ItemService = Depends(get_item_service),
) -> WorkflowService:
    """Build request-scoped workflow service.

    Args:
        request: Incoming HTTP request.
        item_service: Item service from dependency chain.

    Return:
        Workflow service instance.
    """
    container = _container_from_request(request=request)
    return container.library().workflow_service(item_service=item_service)


def get_knowledge_service(
    request: Request,
    item_service: ItemService = Depends(get_item_service),
) -> KnowledgeService:
    """Build request-scoped knowledge service.

    Args:
        request: Incoming HTTP request.
        item_service: Item service from dependency chain.

    Return:
        Knowledge service instance.
    """
    container = _container_from_request(request=request)
    return container.library().knowledge_service(item_service=item_service)


def get_agent_service(
    request: Request,
    repository: AgentRepository = Depends(get_agent_repository),
) -> AgentService:
    """Build request-scoped agent service.

    Args:
        request: Incoming HTTP request.
        repository: Agent repository from dependency chain.

    Return:
        Agent service instance.
    """
    container = _container_from_request(request=request)
    return container.library().agent_service(repository=repository)


def get_librarian_service(
    request: Request,
    provider_repo: LibrarianProviderRepository = Depends(get_librarian_repository),
    secret_repo: ProviderSecretRepository = Depends(get_secret_repository),
) -> LibrarianService:
    """Build request-scoped librarian service.

    Args:
        request: Incoming HTTP request.
        provider_repo: Librarian provider repository from dependency chain.
        secret_repo: Provider secret repository from dependency chain.

    Return:
        Librarian service instance.
    """
    container = _container_from_request(request=request)
    return container.library().librarian_service(
        provider_repo=provider_repo,
        secret_repo=secret_repo,
    )


def get_usage_service(
    request: Request,
    usage_repo: UsageRepository = Depends(get_usage_repository),
) -> UsageService:
    """Build request-scoped usage service.

    Args:
        request: Incoming HTTP request.
        usage_repo: Usage repository from dependency chain.

    Return:
        Usage service instance.
    """
    container = _container_from_request(request=request)
    return container.library().usage_service(usage_repo=usage_repo)
