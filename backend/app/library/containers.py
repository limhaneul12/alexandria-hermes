"""Dependency-injector container for library bounded context."""

from __future__ import annotations

from app.library.application.agent_service import AgentService
from app.library.application.category_service import CategoryService
from app.library.application.context_service import ContextService
from app.library.application.item_service import ItemService
from app.library.application.knowledge_service import KnowledgeService
from app.library.application.librarian_service import LibrarianService
from app.library.application.prompt_service import PromptService
from app.library.application.skill_service import SkillService
from app.library.application.usage_service import UsageService
from app.library.application.use_cases.minio_archive.import_archive_items import (
    MinioArchiveImportUseCase,
)
from app.library.application.use_cases.minio_archive.list_archive_items import (
    ListMinioArchiveItemsUseCase,
)
from app.library.application.workflow_service import WorkflowService
from app.library.infrastructure.repositories import (
    ProviderSecretRepository,
    SqlAlchemyAgentRepository,
    SqlAlchemyCategoryRepository,
    SqlAlchemyContextRepository,
    SqlAlchemyItemRepository,
    SqlAlchemyLibrarianProviderRepository,
    SqlAlchemyUsageRepository,
)
from dependency_injector import containers, providers
from sqlalchemy.ext.asyncio import AsyncSession


class LibraryContainer(containers.DeclarativeContainer):
    """Container for library bounded-context components."""

    db_session = providers.Dependency(instance_of=AsyncSession)
    item_repo = providers.Factory(SqlAlchemyItemRepository, session=db_session)
    usage_repo = providers.Factory(SqlAlchemyUsageRepository, session=db_session)
    category_repo = providers.Factory(SqlAlchemyCategoryRepository, session=db_session)
    context_repo = providers.Factory(SqlAlchemyContextRepository, session=db_session)
    agent_repo = providers.Factory(SqlAlchemyAgentRepository, session=db_session)
    librarian_provider_repo = providers.Factory(
        SqlAlchemyLibrarianProviderRepository,
        session=db_session,
    )
    provider_secret_repo = providers.Factory(
        ProviderSecretRepository, session=db_session
    )

    item_service = providers.Factory(ItemService, item_repo=item_repo)
    usage_service = providers.Factory(UsageService, usage_repo=usage_repo)
    category_service = providers.Factory(
        CategoryService,
        category_repo=category_repo,
    )
    context_service = providers.Factory(
        ContextService,
        repository=context_repo,
    )
    skill_service = providers.Factory(
        SkillService,
        item_service=item_service,
    )
    prompt_service = providers.Factory(
        PromptService,
        item_service=item_service,
    )
    workflow_service = providers.Factory(
        WorkflowService,
        item_service=item_service,
    )
    knowledge_service = providers.Factory(
        KnowledgeService,
        item_service=item_service,
    )
    agent_service = providers.Factory(
        AgentService,
        repository=agent_repo,
    )
    librarian_service = providers.Factory(
        LibrarianService,
        provider_repo=librarian_provider_repo,
        secret_repo=provider_secret_repo,
    )
    minio_archive_list_use_case = providers.Factory(
        ListMinioArchiveItemsUseCase,
        provider_repo=librarian_provider_repo,
        secret_repo=provider_secret_repo,
    )
    minio_archive_import_use_case = providers.Factory(
        MinioArchiveImportUseCase,
        provider_repo=librarian_provider_repo,
        secret_repo=provider_secret_repo,
        item_service=item_service,
    )
