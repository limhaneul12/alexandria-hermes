"""Behavior tests for library MINIO archive discovery."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime

from app.library.application.use_cases.minio_archive.list_archive_items import (
    ListMinioArchiveItemsUseCase,
)
from app.library.domain.contracts.librarian_provider_contracts import (
    LibrarianProviderCreate,
    LibrarianProviderUpdate,
)
from app.library.domain.event_enum.item_enums import (
    CreatedByType,
    ItemStatus,
    ItemType,
    SourceType,
)
from app.library.domain.entities.read_models import LibrarianProvider
from app.library.domain.repositories.librarian_repository import (
    ILibrarianProviderRepository,
    IProviderSecretRepository,
)
from app.platform.storage.minio_object_listing import MinioObjectListingClient
from app.platform.storage.minio_types import MinioObject


class FakeProviderRepository(ILibrarianProviderRepository):
    """In-memory provider repository for MINIO archive tests."""

    def __init__(self, providers: list[LibrarianProvider]) -> None:
        """Store providers returned by list_all."""
        self.providers = providers

    async def get(self, provider_id: str) -> LibrarianProvider | None:
        """Return one provider by ID."""
        provider = next(
            (provider for provider in self.providers if provider.id == provider_id),
            None,
        )
        return provider

    async def list_all(self) -> list[LibrarianProvider]:
        """Return configured providers."""
        return self.providers

    async def create(self, payload: LibrarianProviderCreate) -> LibrarianProvider:
        """Create is outside this test boundary."""
        raise NotImplementedError

    async def update(
        self, provider_id: str, payload: LibrarianProviderUpdate
    ) -> LibrarianProvider:
        """Update is outside this test boundary."""
        raise NotImplementedError

    async def delete(self, provider_id: str) -> None:
        """Delete is outside this test boundary."""
        raise NotImplementedError


class FakeSecretRepository(IProviderSecretRepository):
    """In-memory provider secret repository for MINIO archive tests."""

    def __init__(self, secret: str | None) -> None:
        """Store one secret value."""
        self.secret = secret

    async def resolve(self, provider_id: str, key_name: str) -> str | None:
        """Return the configured secret."""
        return self.secret

    async def set_secret(self, *, provider_id: str, key_name: str, value: str) -> None:
        """Secret mutation is outside this test boundary."""
        raise NotImplementedError

    async def delete_for_provider(self, provider_id: str, key_name: str) -> None:
        """Secret deletion is outside this test boundary."""
        raise NotImplementedError


def _minio_provider(endpoint: str) -> LibrarianProvider:
    now = datetime.now(UTC)
    return LibrarianProvider(
        id="provider-1",
        name="local minio",
        provider_type="MINIO",
        auth_type="API_KEY",
        enabled=True,
        config={"endpoint": endpoint, "bucket": "archive", "prefix": "skills/"},
        created_at=now,
        updated_at=now,
    )


def test_minio_archive_service_preserves_existing_payload_shape(
    monkeypatch,
) -> None:
    """Library service exposes normalized MINIO objects as archive item payloads."""

    def fake_list_objects(
        self: MinioObjectListingClient,
        **kwargs: object,
    ) -> list[MinioObject]:
        return [
            MinioObject(
                key="skills/a.md",
                size=7,
                etag="etag-1",
                last_modified=datetime(2026, 1, 2, tzinfo=UTC),
            )
        ]

    monkeypatch.setattr(
        "app.platform.storage.minio_object_listing.MinioObjectListingClient.list_objects",
        fake_list_objects,
    )
    use_case = ListMinioArchiveItemsUseCase(
        provider_repo=FakeProviderRepository(
            [_minio_provider("https://objects.example.com")]
        ),
        secret_repo=FakeSecretRepository("access:secret"),
    )

    items = asyncio.run(use_case.execute(limit=10))

    assert items[0].title == "a.md"
    assert items[0].content == "s3://archive/skills/a.md"
    assert items[0].tags == ["minio", "archive"]
    assert items[0].item_type is ItemType.KNOWLEDGE
    assert items[0].status is ItemStatus.ACTIVE
    assert items[0].source_type is SourceType.IMPORTED
    assert items[0].created_by_type is CreatedByType.LIBRARIAN
    assert items[0].details == {
        "source": "MINIO",
        "endpoint": "https://objects.example.com",
        "bucket": "archive",
        "object_key": "skills/a.md",
        "size": 7,
        "etag": "etag-1",
        "version": "object",
    }
