"""UUID identifier behavior for the backend-owned archive database."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID

import anyio

from app.library.domain.entities.enums import (
    AuthType,
    CreatedByType,
    ItemStatus,
    ItemType,
    ProviderType,
    SelectionSource,
    SourceType,
)
from app.library.infrastructure.repositories.category_repository import (
    SqlAlchemyCategoryRepository,
)
from app.library.infrastructure.repositories.item_repository import SqlAlchemyItemRepository
from app.library.infrastructure.repositories.librarian_repository import (
    ProviderSecretRepository,
    SqlAlchemyLibrarianProviderRepository,
)
from app.library.infrastructure.repositories.usage_repository import SqlAlchemyUsageRepository
from app.shared.infrastructure.database import Database
from app.shared.types.extra_types import JSONValue


@asynccontextmanager
async def _temporary_database(path: Path) -> AsyncIterator[Database]:
    database = Database(database_url=f"sqlite+aiosqlite:///{path}", create_schema=True)
    await database.initialize()
    try:
        yield database
    finally:
        await database.shutdown()


def _assert_uuid4(value: str) -> None:
    parsed = UUID(value, version=4)
    assert str(parsed) == value


def _item_payload(category_id: str | None) -> dict[str, JSONValue]:
    now = datetime.now(UTC)
    return {
        "item_type": ItemType.SKILL.value,
        "title": "UUID searchable skill",
        "summary": "Use non-enumerable identifiers",
        "content": "UUID identifiers should still work with FTS search.",
        "category_id": category_id,
        "tags": ["security", "uuid"],
        "status": ItemStatus.ACTIVE.value,
        "source_type": SourceType.USER_CREATED.value,
        "created_by_type": CreatedByType.USER.value,
        "created_by_name": "test-user",
        "created_at": now,
        "updated_at": now,
        "details": {},
        "is_archived": False,
    }


def _provider_payload() -> dict[str, JSONValue]:
    now = datetime.now(UTC)
    return {
        "name": "local librarian",
        "provider_type": ProviderType.LOCAL.value,
        "auth_type": AuthType.API_KEY.value,
        "enabled": True,
        "config": {"base_url": "http://localhost"},
        "created_at": now,
        "updated_at": now,
        "secrets": {"api_key": "first-secret"},
    }


def test_library_repositories_generate_uuid4_identifiers(tmp_path: Path) -> None:
    """Repository-created IDs should be UUIDv4 strings, not enumerable integers."""

    async def scenario() -> None:
        async with _temporary_database(tmp_path / "uuid.db") as database:
            async with database.session() as session:
                categories = SqlAlchemyCategoryRepository(session=session)
                items = SqlAlchemyItemRepository(session=session)
                usage = SqlAlchemyUsageRepository(session=session)
                providers = SqlAlchemyLibrarianProviderRepository(session=session)
                secrets = ProviderSecretRepository(session=session)

                root = await categories.create(name="Root")
                child = await categories.create(name="Child", parent_id=root.id)
                item = await items.create(payload=_item_payload(child.id))
                provider = await providers.create(_provider_payload())
                usage_event = await usage.create(
                    {
                        "item_id": item.id,
                        "item_type": item.item_type,
                        "agent_name": "codex",
                        "librarian_provider": provider.name,
                        "query": "uuid",
                        "selection_source": SelectionSource.SEARCH.value,
                        "used_at": datetime.now(UTC),
                        "success": True,
                        "feedback": {"comment": "works"},
                    }
                )

                for value in [root.id, child.id, item.id, provider.id, usage_event.id]:
                    _assert_uuid4(value)

                assert child.parent_id == root.id
                assert item.category_id == child.id
                assert usage_event.item_id == item.id
                assert await secrets.resolve(provider.id, "api_key") == "first-secret"
                assert [result.id for result in await items.search("UUID")] == [item.id]

    anyio.run(scenario)
