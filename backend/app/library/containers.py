"""Dependency-injector container for library bounded context."""

from __future__ import annotations

from app.library.application.category_service import CategoryService
from app.library.application.item_search_service import ItemSearchService
from app.library.application.item_service import ItemService
from app.library.application.knowledge_service import KnowledgeService
from app.library.application.prompt_service import PromptService
from app.library.application.skill_service import SkillService
from app.library.application.usage_service import UsageService
from app.library.application.workflow_service import WorkflowService
from app.library.infrastructure.repositories.category_repository import (
    SqlAlchemyCategoryRepository,
)
from app.library.infrastructure.repositories.item_repository import (
    SqlAlchemyItemRepository,
)
from app.library.infrastructure.repositories.usage_repository import (
    SqlAlchemyUsageRepository,
)
from dependency_injector import containers, providers
from sqlalchemy.ext.asyncio import AsyncSession


class LibraryContainer(containers.DeclarativeContainer):
    """Container for shared library asset components."""

    db_session = providers.Dependency(instance_of=AsyncSession)
    item_repo = providers.Factory(SqlAlchemyItemRepository, session=db_session)
    usage_repo = providers.Factory(SqlAlchemyUsageRepository, session=db_session)
    category_repo = providers.Factory(SqlAlchemyCategoryRepository, session=db_session)

    item_service = providers.Factory(ItemService, item_repo=item_repo)
    item_search_service = providers.Factory(ItemSearchService, item_repo=item_repo)
    usage_service = providers.Factory(UsageService, usage_repo=usage_repo)
    category_service = providers.Factory(
        CategoryService,
        category_repo=category_repo,
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
