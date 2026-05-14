"""UUID identifier behavior for the backend-owned archive database."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID

import anyio

from app.library.domain.contracts.item_contracts import ItemCreate
from app.library.domain.contracts.librarian_provider_contracts import (
    LibrarianProviderCreate,
)
from app.library.domain.contracts.usage_contracts import UsageCreate
from app.library.domain.event_enum.item_enums import (
    CreatedByType,
    ItemStatus,
    ItemType,
    SourceType,
)
from app.library.domain.event_enum.provider_enums import AuthType, ProviderType
from app.library.domain.event_enum.usage_enums import SelectionSource
from app.library.infrastructure.repositories.category_repository import (
    SqlAlchemyCategoryRepository,
)
from app.library.infrastructure.repositories.item_repository import (
    SqlAlchemyItemRepository,
)
from app.library.infrastructure.repositories.librarian_repository import (
    ProviderSecretRepository,
    SqlAlchemyLibrarianProviderRepository,
)
from app.library.infrastructure.repositories.usage_repository import (
    SqlAlchemyUsageRepository,
)
from app.shared.infrastructure.database import Database


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


def _item_payload(category_id: str | None) -> ItemCreate:
    now = datetime.now(UTC)
    return ItemCreate(
        item_type=ItemType.SKILL,
        title="UUID searchable skill",
        summary="Use non-enumerable identifiers",
        content="UUID identifiers should still work with FTS search.",
        category_id=category_id,
        tags=["security", "uuid"],
        status=ItemStatus.ACTIVE,
        source_type=SourceType.USER_CREATED,
        created_by_type=CreatedByType.USER,
        created_by_name="test-user",
        created_at=now,
        updated_at=now,
        details={},
        is_archived=False,
    )


def _provider_payload() -> LibrarianProviderCreate:
    now = datetime.now(UTC)
    return LibrarianProviderCreate(
        name="openai librarian",
        provider_type=ProviderType.OPENAI,
        auth_type=AuthType.API_KEY,
        enabled=True,
        config={"model": "gpt-4o-mini"},
        created_at=now,
        updated_at=now,
    )


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
                await secrets.set_secret(
                    provider_id=provider.id,
                    key_name="api_key",
                    value="first-secret",
                )
                usage_event = await usage.create(
                    UsageCreate(
                        item_id=item.id,
                        item_type=item.item_type,
                        agent_name="codex",
                        librarian_provider=provider.name,
                        query="uuid",
                        selection_source=SelectionSource.SEARCH,
                        used_at=datetime.now(UTC),
                        success=True,
                        feedback={"comment": "works"},
                    )
                )

                for value in [root.id, child.id, item.id, provider.id, usage_event.id]:
                    _assert_uuid4(value)

                assert child.parent_id == root.id
                assert item.category_id == child.id
                assert usage_event.item_id == item.id
                assert await secrets.resolve(provider.id, "api_key") == "first-secret"
                assert [result.id for result in await items.search("UUID")] == [item.id]

    anyio.run(scenario)
