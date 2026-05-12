"""Behavior tests for library DB repository contracts."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from pathlib import Path

import anyio
import pytest

from app.library.domain.entities.enums import (
    AuthType,
    CreatedByType,
    ItemStatus,
    ItemType,
    ProviderType,
    SelectionSource,
    SourceType,
)
from app.library.infrastructure.repositories.agent_repository import (
    SqlAlchemyAgentRepository,
)
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
from app.shared.exceptions import NotFoundError
from app.shared.infrastructure.database import Database
from app.shared.types.extra_types import JSONValue


@asynccontextmanager
async def _temporary_database(path: Path) -> AsyncIterator[Database]:
    database = Database(database_url=f"sqlite+aiosqlite:///{path}")
    await database.initialize()
    try:
        yield database
    finally:
        await database.shutdown()


def _now() -> datetime:
    return datetime.now(UTC)


def _agent_payload(name: str = "codex") -> dict[str, JSONValue]:
    now = _now()
    return {
        "name": name,
        "provider": "openai",
        "description": "Uses the library",
        "capabilities": ["code"],
        "preferred_librarian_provider": None,
        "created_at": now,
        "updated_at": now,
    }


def _item_payload(title: str = "Usage target") -> dict[str, JSONValue]:
    now = _now()
    return {
        "item_type": ItemType.SKILL.value,
        "title": title,
        "summary": "Used by agents",
        "content": "A reusable action",
        "category_id": None,
        "tags": ["usage"],
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
    now = _now()
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


def test_category_repository_orders_hierarchy_and_reports_missing_mutations(
    tmp_path: Path,
) -> None:
    """Category repository should persist hierarchy state and reject missing targets."""

    async def scenario() -> None:
        async with _temporary_database(tmp_path / "categories.db") as database:
            async with database.session() as session:
                repository = SqlAlchemyCategoryRepository(session=session)
                root = await repository.create(name="Root")
                child = await repository.create(name="Child", parent_id=root.id)
                sibling = await repository.create(name="Sibling", parent_id=root.id)

                await repository.move(sibling.id, parent_id=None, position=2)
                await repository.reorder(category_id=child.id, position=3)
                await session.commit()

                tree = await repository.build_tree()
                descendants = await repository.descendants_of(root.id)

                assert [
                    (node.name, node.parent_id, node.position) for node in tree
                ] == [
                    ("Root", None, 1),
                    ("Sibling", None, 2),
                    ("Child", root.id, 3),
                ]
                assert [node.name for node in descendants] == ["Child"]
                assert await repository.max_depth(child.id) == 1
                assert await repository.has_descendant(root.id, child.id) is True

                with pytest.raises(NotFoundError, match="Category not found: 404"):
                    await repository.update_name(404, name="Missing")

    anyio.run(scenario)


def test_agent_repository_persists_updates_and_reports_missing_deletes(
    tmp_path: Path,
) -> None:
    """Agent repository should expose create/read/update/delete contracts."""

    async def scenario() -> None:
        async with _temporary_database(tmp_path / "agents.db") as database:
            async with database.session() as session:
                repository = SqlAlchemyAgentRepository(session=session)
                created = await repository.create(_agent_payload())

                assert [agent.name for agent in await repository.list_all()] == [
                    "codex"
                ]

                updated = await repository.update(
                    created.id,
                    {"description": "Uses skills", "capabilities": ["code", "review"]},
                )
                assert updated.description == "Uses skills"
                assert updated.capabilities == ["code", "review"]

                await repository.delete(created.id)
                assert await repository.get(created.id) is None

                with pytest.raises(NotFoundError, match="Agent not found: 404"):
                    await repository.delete(404)

    anyio.run(scenario)


def test_usage_repository_returns_recent_and_popular_successful_usage(
    tmp_path: Path,
) -> None:
    """Usage repository should aggregate only successful usage by default."""

    async def scenario() -> None:
        async with _temporary_database(tmp_path / "usage.db") as database:
            async with database.session() as session:
                item_repository = SqlAlchemyItemRepository(session=session)
                usage_repository = SqlAlchemyUsageRepository(session=session)
                item = await item_repository.create(payload=_item_payload())
                other = await item_repository.create(
                    payload=_item_payload("Other target")
                )

                await usage_repository.record_event(
                    item_id=item.id,
                    item_type=item.item_type,
                    agent_name="codex",
                    query="deploy",
                    librarian_provider=None,
                    selection_source=SelectionSource.SEARCH,
                    success=True,
                    feedback="worked",
                )
                await usage_repository.record_event(
                    item_id=item.id,
                    item_type=item.item_type,
                    agent_name="codex",
                    query="deploy",
                    librarian_provider=None,
                    selection_source=SelectionSource.SEARCH,
                    success=False,
                    feedback="missed",
                )
                await usage_repository.record_event(
                    item_id=other.id,
                    item_type=other.item_type,
                    agent_name="codex",
                    query="other",
                    librarian_provider=None,
                    selection_source=SelectionSource.RECOMMENDATION,
                    success=True,
                    feedback=None,
                )

                assert [
                    event.item_id for event in await usage_repository.recent(limit=2)
                ] == [
                    other.id,
                    item.id,
                ]
                await usage_repository.record_event(
                    item_id=other.id,
                    item_type=other.item_type,
                    agent_name="codex",
                    query="other",
                    librarian_provider=None,
                    selection_source=SelectionSource.RECOMMENDATION,
                    success=True,
                    feedback=None,
                )

                assert await usage_repository.popular() == [(other.id, 2), (item.id, 1)]
                assert dict(await usage_repository.popular(success_only=False)) == {
                    item.id: 2,
                    other.id: 2,
                }
                assert [
                    event.success
                    for event in await usage_repository.list_by_item(item.id)
                ] == [
                    False,
                    True,
                ]

    anyio.run(scenario)


def test_librarian_provider_repository_replaces_and_resolves_secrets(
    tmp_path: Path,
) -> None:
    """Provider repositories should persist provider config while managing secrets separately."""

    async def scenario() -> None:
        async with _temporary_database(tmp_path / "providers.db") as database:
            async with database.session() as session:
                provider_repository = SqlAlchemyLibrarianProviderRepository(
                    session=session
                )
                secret_repository = ProviderSecretRepository(session=session)
                provider = await provider_repository.create(_provider_payload())

                assert (
                    await secret_repository.resolve(provider.id, "api_key")
                    == "first-secret"
                )

                updated = await provider_repository.update(
                    provider.id,
                    {"enabled": False, "secrets": {"api_key": "second-secret"}},
                )
                await secret_repository.set_secret(
                    provider_id=provider.id,
                    key_name="tenant",
                    value="alexandria",
                )
                await secret_repository.delete_for_provider(provider.id, "tenant")

                assert updated.enabled is False
                assert (
                    await secret_repository.resolve(provider.id, "api_key")
                    == "second-secret"
                )
                assert await secret_repository.resolve(provider.id, "tenant") is None

                with pytest.raises(NotFoundError, match="Provider not found: 404"):
                    await provider_repository.update(404, {"enabled": True})

    anyio.run(scenario)
