"""Behavior tests for library DB repository contracts."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from pathlib import Path

import anyio
import pytest
from app.librarian.domain.contracts.agent_contracts import AgentCreate, AgentUpdate
from app.library.domain.contracts.item_contracts import ItemCreate
from app.connections.domain.contracts.librarian_provider_contracts import (
    LibrarianProviderCreate,
    LibrarianProviderUpdate,
)
from app.library.domain.event_enum.item_enums import (
    CreatedByType,
    ItemStatus,
    ItemType,
    SourceType,
)
from app.connections.domain.event_enum.provider_enums import AuthType, ProviderType
from app.library.domain.event_enum.usage_enums import SelectionSource
from app.library.domain.entities.read_models import Category
from app.connections.infrastructure.models.librarian_provider_models import (
    ProviderSecretORM,
)
from app.librarian.infrastructure.repositories.agent_repository import (
    SqlAlchemyAgentRepository,
)
from app.library.infrastructure.repositories.categories.hierarchy import descendants_of
from app.library.infrastructure.repositories.category_repository import (
    SqlAlchemyCategoryRepository,
)
from app.library.infrastructure.repositories.item_repository import (
    SqlAlchemyItemRepository,
)
from app.connections.infrastructure.repositories.librarian_repository import (
    ProviderSecretRepository,
    SqlAlchemyLibrarianProviderRepository,
)
from app.library.infrastructure.repositories.usage_repository import (
    SqlAlchemyUsageRepository,
)
from app.shared.exceptions import NotFoundError
from app.shared.infrastructure.database import Database
from sqlalchemy import select


@asynccontextmanager
async def _temporary_database(path: Path) -> AsyncIterator[Database]:
    database = Database(database_url=f"sqlite+aiosqlite:///{path}", create_schema=True)
    await database.initialize()
    try:
        yield database
    finally:
        await database.shutdown()


def _now() -> datetime:
    return datetime.now(UTC)


def _agent_payload(name: str = "codex") -> AgentCreate:
    now = _now()
    return AgentCreate(
        name=name,
        provider="openai",
        description="Uses the library",
        capabilities=["code"],
        preferred_librarian_provider="00000000-0000-4000-8000-000000000777",
        preferred_librarian_model="gpt-5.5",
        max_librarian_agents=3,
        librarian_role_prompt="Act as a codebase librarian.",
        librarian_role="SPECIALIST",
        librarian_specialties=["code"],
        librarian_routing_priority=20,
        librarian_enabled=True,
        created_at=now,
        updated_at=now,
    )


def _item_payload(title: str = "Usage target") -> ItemCreate:
    now = _now()
    return ItemCreate(
        item_type=ItemType.SKILL,
        title=title,
        summary="Used by agents",
        content="A reusable action",
        category_id=None,
        tags=["usage"],
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
    now = _now()
    return LibrarianProviderCreate(
        name="openai librarian",
        provider_type=ProviderType.OPENAI,
        auth_type=AuthType.API_KEY,
        enabled=True,
        config={"model": "gpt-4o-mini"},
        created_at=now,
        updated_at=now,
    )


def test_category_hierarchy_traversal_preserves_ordered_adjacency() -> None:
    """Category traversal should preserve nearest ordered-adjacency descendants."""
    now = _now()
    root = Category("root", "Root", None, 1, now, now)
    alpha = Category("alpha", "Alpha", root.id, 1, now, now)
    beta = Category("beta", "Beta", root.id, 2, now, now)
    alpha_child = Category("alpha-child", "Alpha child", alpha.id, 1, now, now)
    beta_child = Category("beta-child", "Beta child", beta.id, 1, now, now)
    nodes = [root, alpha, beta, alpha_child, beta_child]

    descendants = descendants_of(nodes, root.id)

    assert [node.id for node in descendants] == [
        alpha.id,
        beta.id,
        alpha_child.id,
        beta_child.id,
    ]


def test_category_repository_orders_hierarchy_and_reports_missing_mutations(
    tmp_path: Path,
) -> None:
    """Category repository should persist hierarchy state and reject missing targets."""

    async def scenario() -> None:
        async with (
            _temporary_database(tmp_path / "categories.db") as database,
            database.session() as session,
        ):
            repository = SqlAlchemyCategoryRepository(session=session)
            root = await repository.create(name="Root")
            child = await repository.create(name="Child", parent_id=root.id)
            sibling = await repository.create(name="Sibling", parent_id=root.id)

            await repository.move(sibling.id, parent_id=None, position=2)
            await repository.reorder(category_id=child.id, position=3)
            await session.commit()

            tree = await repository.build_tree()
            descendants = await repository.descendants_of(root.id)

            assert [(node.name, node.parent_id, node.position) for node in tree] == [
                ("Root", None, 1),
                ("Sibling", None, 2),
                ("Child", root.id, 3),
            ]
            assert [node.name for node in descendants] == ["Child"]
            assert await repository.max_depth(child.id) == 1
            assert await repository.has_descendant(root.id, child.id) is True

            missing_id = "00000000-0000-4000-8000-000000000404"

            with pytest.raises(
                NotFoundError, match=f"Category not found: {missing_id}"
            ):
                await repository.update_name(missing_id, name="Missing")

    anyio.run(scenario)


def test_agent_repository_persists_updates_and_reports_missing_deletes(
    tmp_path: Path,
) -> None:
    """Agent repository should expose create/read/update/delete contracts."""

    async def scenario() -> None:
        async with (
            _temporary_database(tmp_path / "agents.db") as database,
            database.session() as session,
        ):
            repository = SqlAlchemyAgentRepository(session=session)
            created = await repository.create(_agent_payload())

            assert [agent.name for agent in await repository.list_all()] == ["codex"]

            updated = await repository.update(
                created.id,
                AgentUpdate(
                    values={
                        "name": "review-codex",
                        "description": "Uses skills",
                        "capabilities": ["code", "review"],
                        "preferred_librarian_provider": "provider-2",
                        "preferred_librarian_model": "gpt-5.4",
                        "max_librarian_agents": 2,
                        "librarian_role_prompt": "Review plans before execution.",
                        "librarian_role": "QUALITY_REVIEWER",
                        "librarian_specialties": ["code", "review"],
                        "librarian_routing_priority": 5,
                        "librarian_enabled": False,
                    }
                ),
            )
            assert updated.name == "review-codex"
            assert updated.description == "Uses skills"
            assert updated.capabilities == ["code", "review"]
            assert updated.preferred_librarian_provider == "provider-2"
            assert updated.preferred_librarian_model == "gpt-5.4"
            assert updated.max_librarian_agents == 2
            assert updated.librarian_role_prompt == "Review plans before execution."
            assert updated.librarian_role == "QUALITY_REVIEWER"
            assert updated.librarian_specialties == ["code", "review"]
            assert updated.librarian_routing_priority == 5
            assert updated.librarian_enabled is False

            await repository.delete(created.id)
            assert await repository.get(created.id) is None

            missing_id = "00000000-0000-4000-8000-000000000404"

            with pytest.raises(NotFoundError, match=f"Agent not found: {missing_id}"):
                await repository.delete(missing_id)

    anyio.run(scenario)


def test_usage_repository_returns_recent_and_popular_successful_usage(
    tmp_path: Path,
) -> None:
    """Usage repository should aggregate only successful usage by default."""

    async def scenario() -> None:
        async with (
            _temporary_database(tmp_path / "usage.db") as database,
            database.session() as session,
        ):
            item_repository = SqlAlchemyItemRepository(session=session)
            usage_repository = SqlAlchemyUsageRepository(session=session)
            item = await item_repository.create(payload=_item_payload())
            other = await item_repository.create(payload=_item_payload("Other target"))

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
                event.success for event in await usage_repository.list_by_item(item.id)
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
        async with (
            _temporary_database(tmp_path / "providers.db") as database,
            database.session() as session,
        ):
            provider_repository = SqlAlchemyLibrarianProviderRepository(session=session)
            secret_repository = ProviderSecretRepository(session=session)
            provider = await provider_repository.create(_provider_payload())
            await secret_repository.set_secret(
                provider_id=provider.id,
                key_name="api_key",
                value="first-secret",
            )
            raw_created_secret = await session.scalar(
                select(ProviderSecretORM.value).where(
                    ProviderSecretORM.provider_id == provider.id,
                    ProviderSecretORM.key_name == "api_key",
                )
            )

            assert raw_created_secret is not None
            assert raw_created_secret.startswith("enc:v1:")
            assert "first-secret" not in raw_created_secret
            assert (
                await secret_repository.resolve(provider.id, "api_key")
                == "first-secret"
            )

            updated = await provider_repository.update(
                provider.id,
                LibrarianProviderUpdate(values={"enabled": False}),
            )
            await secret_repository.set_secret(
                provider_id=provider.id,
                key_name="api_key",
                value="second-secret",
            )
            await secret_repository.set_secret(
                provider_id=provider.id,
                key_name="tenant",
                value="alexandria",
            )
            await secret_repository.delete_for_provider(provider.id, "tenant")

            assert updated.enabled is False
            raw_updated_secret = await session.scalar(
                select(ProviderSecretORM.value).where(
                    ProviderSecretORM.provider_id == provider.id,
                    ProviderSecretORM.key_name == "api_key",
                )
            )
            assert raw_updated_secret is not None
            assert raw_updated_secret.startswith("enc:v1:")
            assert "second-secret" not in raw_updated_secret
            assert (
                await secret_repository.resolve(provider.id, "api_key")
                == "second-secret"
            )
            assert await secret_repository.resolve(provider.id, "tenant") is None

            missing_id = "00000000-0000-4000-8000-000000000404"

            with pytest.raises(
                NotFoundError, match=f"Provider not found: {missing_id}"
            ):
                await provider_repository.update(missing_id, {"enabled": True})

    anyio.run(scenario)
