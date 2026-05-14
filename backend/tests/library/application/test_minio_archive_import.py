"""Behavior tests for external MINIO archive imports."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from typing import cast

from app.library.application.item_service import ItemService
from app.library.application.use_cases.minio_archive.import_archive_items import (
    MinioArchiveImportUseCase,
)
from app.library.domain.contracts.librarian_provider_contracts import (
    LibrarianProviderCreate,
    LibrarianProviderUpdate,
)
from app.library.domain.entities.read_models import LibrarianProvider
from app.library.domain.event_enum.item_enums import (
    CreatedByType,
    ItemStatus,
    ItemType,
    SourceType,
)
from app.library.domain.repositories.librarian_repository import (
    ILibrarianProviderRepository,
    IProviderSecretRepository,
)
from app.library.domain.types.item_payload_types import (
    LibraryItemListResult,
    LibraryItemPayload,
)
from app.platform.storage.minio_object_content import MinioObjectContentClient
from app.platform.storage.minio_object_listing import MinioObjectListingClient
from app.platform.storage.minio_types import MinioObject
from app.shared.types.extra_types import JSONObject


class FakeProviderRepository(ILibrarianProviderRepository):
    """In-memory provider repository for import tests."""

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
        self,
        provider_id: str,
        payload: LibrarianProviderUpdate,
    ) -> LibrarianProvider:
        """Update is outside this test boundary."""
        raise NotImplementedError

    async def delete(self, provider_id: str) -> None:
        """Delete is outside this test boundary."""
        raise NotImplementedError


class FakeSecretRepository(IProviderSecretRepository):
    """In-memory provider secret repository for import tests."""

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


class FakeItemService:
    """Behavior fake for item catalog side effects."""

    def __init__(self, existing_items: list[LibraryItemPayload] | None = None) -> None:
        """Store existing and created item payloads."""
        self.existing_items = existing_items or []
        self.created_items: list[LibraryItemPayload] = []

    async def list_items(self, limit: int = 1000) -> LibraryItemListResult:
        """Return existing item payloads for duplicate detection."""
        return self.existing_items, len(self.existing_items)

    async def create_item(
        self,
        *,
        item_type: ItemType,
        title: str,
        summary: str | None,
        content: str,
        category_id: str | None,
        tags: list[str],
        status: ItemStatus,
        source_type: SourceType,
        created_by_type: CreatedByType,
        created_by_name: str,
        details: JSONObject,
    ) -> LibraryItemPayload:
        """Persist a created item payload in memory."""
        now = datetime(2026, 1, 2, tzinfo=UTC)
        payload: LibraryItemPayload = {
            "id": f"item-{len(self.created_items) + 1}",
            "item_type": item_type,
            "title": title,
            "summary": summary,
            "content": content,
            "category_id": category_id,
            "tags": tags,
            "status": status,
            "source_type": source_type,
            "created_by_type": created_by_type,
            "created_by_name": created_by_name,
            "details": details,
            "created_at": now,
            "updated_at": now,
        }
        self.created_items.append(payload)
        return payload


def _minio_provider(endpoint: str) -> LibrarianProvider:
    now = datetime(2026, 1, 2, tzinfo=UTC)
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


def _object(key: str) -> MinioObject:
    return MinioObject(
        key=key,
        size=128,
        etag="etag-1",
        last_modified=datetime(2026, 1, 2, tzinfo=UTC),
    )


def _use_case(item_service: FakeItemService) -> MinioArchiveImportUseCase:
    return MinioArchiveImportUseCase(
        provider_repo=FakeProviderRepository(
            [_minio_provider("https://objects.example.com")]
        ),
        secret_repo=FakeSecretRepository("access:secret"),
        item_service=cast(ItemService, item_service),
    )


def test_minio_archive_import_scan_infers_library_cards_when_librarian_is_absent(
    monkeypatch,
) -> None:
    """MINIO sync proposes reviewable library cards without requiring an LLM."""

    def fake_list_objects(
        self: MinioObjectListingClient,
        **kwargs: object,
    ) -> list[MinioObject]:
        return [_object("skills/fastapi-di.md"), _object("images/logo.png")]

    def fake_read_text_object(
        self: MinioObjectContentClient,
        **kwargs: object,
    ) -> str:
        return "\n".join(
            [
                "title: FastAPI Dependency Injection",
                "summary: Dependency patterns for backend agents",
                "purpose: Teach agents how to wire FastAPI dependencies.",
                "Body with useful examples.",
            ]
        )

    monkeypatch.setattr(
        "app.platform.storage.minio_object_listing.MinioObjectListingClient.list_objects",
        fake_list_objects,
    )
    monkeypatch.setattr(
        "app.platform.storage.minio_object_content.MinioObjectContentClient.read_text_object",
        fake_read_text_object,
    )
    use_case = _use_case(FakeItemService())

    candidates = asyncio.run(use_case.scan(limit=10))

    assert len(candidates) == 1
    assert candidates[0].title == "FastAPI Dependency Injection"
    assert candidates[0].summary == "Dependency patterns for backend agents"
    assert candidates[0].item_type is ItemType.SKILL
    assert candidates[0].tags == ["external-archive", "archive", "skills"]
    assert candidates[0].needs_review is False
    assert candidates[0].details["storage"] == {
        "type": "OBJECT_STORAGE",
        "provider_type": "MINIO",
        "provider_id": "provider-1",
        "endpoint": "https://objects.example.com",
        "bucket": "archive",
        "object_key": "skills/fastapi-di.md",
        "etag": "etag-1",
        "size": 128,
    }


def test_minio_archive_import_scan_detects_prompt_files(monkeypatch) -> None:
    """MINIO scan classifies prompt objects with reusable prompt metadata."""

    def fake_list_objects(
        self: MinioObjectListingClient,
        **kwargs: object,
    ) -> list[MinioObject]:
        return [_object("prompts/fastapi-review.prompt.md")]

    def fake_read_text_object(
        self: MinioObjectContentClient,
        **kwargs: object,
    ) -> str:
        return "\n".join(
            [
                "type: prompt",
                "title: FastAPI Review Prompt",
                "kind: user_template",
                "domain: development",
                "task_type: code_review",
                "Review this diff: {{diff}}",
            ]
        )

    monkeypatch.setattr(
        "app.platform.storage.minio_object_listing.MinioObjectListingClient.list_objects",
        fake_list_objects,
    )
    monkeypatch.setattr(
        "app.platform.storage.minio_object_content.MinioObjectContentClient.read_text_object",
        fake_read_text_object,
    )
    use_case = _use_case(FakeItemService())

    candidates = asyncio.run(use_case.scan(limit=10))

    assert len(candidates) == 1
    assert candidates[0].item_type is ItemType.PROMPT
    assert candidates[0].title == "FastAPI Review Prompt"
    assert candidates[0].details["content_format"] == "MARKDOWN"
    assert candidates[0].details["prompt_kind"] == "USER_TEMPLATE"
    assert candidates[0].details["prompt_domain"] == "DEVELOPMENT"
    assert candidates[0].details["prompt_task_type"] == "CODE_REVIEW"
    assert candidates[0].details["input_variables"] == [
        {
            "name": "diff",
            "required": True,
            "description": None,
            "default_value": None,
            "example": None,
            "input_type": "text",
        }
    ]


def test_minio_archive_import_linked_persists_metadata_without_copying_original(
    monkeypatch,
) -> None:
    """Importing stores a DB catalog row linked to the MINIO original."""

    def fake_list_objects(
        self: MinioObjectListingClient,
        **kwargs: object,
    ) -> list[MinioObject]:
        return [_object("workflows/release-checklist.md")]

    def fake_read_text_object(
        self: MinioObjectContentClient,
        **kwargs: object,
    ) -> str:
        return "# Release checklist\nworkflow\n- test\n- deploy"

    monkeypatch.setattr(
        "app.platform.storage.minio_object_listing.MinioObjectListingClient.list_objects",
        fake_list_objects,
    )
    monkeypatch.setattr(
        "app.platform.storage.minio_object_content.MinioObjectContentClient.read_text_object",
        fake_read_text_object,
    )
    item_service = FakeItemService()
    use_case = _use_case(item_service)

    result = asyncio.run(use_case.import_linked(limit=10))

    assert result.imported_count == 1
    assert result.skipped_count == 0
    assert result.item_ids == ["item-1"]
    assert item_service.created_items[0]["item_type"] is ItemType.WORKFLOW
    assert item_service.created_items[0]["source_type"] is SourceType.IMPORTED
    assert item_service.created_items[0]["created_by_type"] is CreatedByType.LIBRARIAN
    assert item_service.created_items[0]["details"]["storage"] == {
        "type": "OBJECT_STORAGE",
        "provider_type": "MINIO",
        "provider_id": "provider-1",
        "endpoint": "https://objects.example.com",
        "bucket": "archive",
        "object_key": "workflows/release-checklist.md",
        "etag": "etag-1",
        "size": 128,
    }
    assert item_service.created_items[0]["details"]["import"] == {
        "mode": "LINKED",
        "confidence": 0.78,
        "needs_review": False,
        "content_hash": item_service.created_items[0]["details"]["import"][
            "content_hash"
        ],
    }


def test_minio_archive_import_linked_skips_existing_storage_refs(
    monkeypatch,
) -> None:
    """Repeated imports skip DB rows that already reference the same object."""

    def fake_list_objects(
        self: MinioObjectListingClient,
        **kwargs: object,
    ) -> list[MinioObject]:
        return [_object("skills/existing.md")]

    def fake_read_text_object(
        self: MinioObjectContentClient,
        **kwargs: object,
    ) -> str:
        return "skill: already imported"

    monkeypatch.setattr(
        "app.platform.storage.minio_object_listing.MinioObjectListingClient.list_objects",
        fake_list_objects,
    )
    monkeypatch.setattr(
        "app.platform.storage.minio_object_content.MinioObjectContentClient.read_text_object",
        fake_read_text_object,
    )
    now = datetime(2026, 1, 2, tzinfo=UTC)
    existing: LibraryItemPayload = {
        "id": "existing-1",
        "item_type": ItemType.SKILL,
        "title": "Existing",
        "summary": None,
        "content": "body",
        "category_id": None,
        "tags": [],
        "status": ItemStatus.ACTIVE,
        "source_type": SourceType.IMPORTED,
        "created_by_type": CreatedByType.LIBRARIAN,
        "created_by_name": "Hermes Importer",
        "details": {
            "storage": {
                "provider_id": "provider-1",
                "bucket": "archive",
                "object_key": "skills/existing.md",
            }
        },
        "created_at": now,
        "updated_at": now,
    }
    item_service = FakeItemService([existing])
    use_case = _use_case(item_service)

    result = asyncio.run(use_case.import_linked(limit=10))

    assert result.imported_count == 0
    assert result.skipped_count == 1
    assert result.item_ids == []
    assert item_service.created_items == []
