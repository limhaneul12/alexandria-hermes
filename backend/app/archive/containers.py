"""Dependency-injector container for archive bounded context."""

from __future__ import annotations

from app.archive.application.minio.use_cases.import_archive_items import (
    MinioArchiveImportUseCase,
)
from app.archive.application.minio.use_cases.list_archive_items import (
    ListMinioArchiveItemsUseCase,
)
from app.connections.domain.repositories.librarian_repository import (
    ILibrarianProviderRepository,
    IProviderSecretRepository,
)
from app.library.application.item_service import ItemService
from dependency_injector import containers, providers
from sqlalchemy.ext.asyncio import AsyncSession


class ArchiveContainer(containers.DeclarativeContainer):
    """Container for optional archive/object-storage connectors."""

    db_session = providers.Dependency(instance_of=AsyncSession)
    item_service = providers.Dependency(instance_of=ItemService)
    librarian_provider_repo = providers.Dependency(
        instance_of=ILibrarianProviderRepository
    )
    provider_secret_repo = providers.Dependency(instance_of=IProviderSecretRepository)
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
