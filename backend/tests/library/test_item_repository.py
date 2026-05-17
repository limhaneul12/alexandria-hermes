"""Behavior tests for library item repository search contracts."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import anyio
import pytest
from app.library.application.item_search_service import ItemSearchService
from app.library.application.item_service import ItemService
from app.library.domain.contracts.item_contracts import ItemCreate, ItemUpdate
from app.library.domain.event_enum.item_enums import (
    CreatedByType,
    ItemStatus,
    ItemType,
    SourceType,
)
from app.library.infrastructure.repositories.item_repository import (
    SqlAlchemyItemRepository,
)
from app.library.infrastructure.repositories.items.fts import build_item_fts_query
from app.main import app
from app.shared.exceptions import NotFoundError
from tests.shared.provider_overrides import override_library_provider
from app.shared.infrastructure.database import Database
from app.shared.types.extra_types import JSONValue
from fastapi.testclient import TestClient


def _item_payload(
    *,
    title: str = "Quote-ready search skill",
    item_type: ItemType = ItemType.SKILL,
    content: str = "Use quote and hyphen safe search terms.",
    summary: str | None = "Search helper",
    tags: list[str] | None = None,
    details: dict[str, JSONValue] | None = None,
) -> ItemCreate:
    now = datetime.now(UTC)
    return ItemCreate(
        item_type=item_type,
        title=title,
        summary=summary,
        content=content,
        category_id=None,
        tags=tags or ["search"],
        status=ItemStatus.ACTIVE,
        source_type=SourceType.USER_CREATED,
        created_by_type=CreatedByType.USER,
        created_by_name="test-user",
        created_at=now,
        updated_at=now,
        details=details or {},
        is_archived=False,
    )


@asynccontextmanager
async def _temporary_database(path: Path) -> AsyncIterator[Database]:
    database = Database(database_url=f"sqlite+aiosqlite:///{path}", create_schema=True)
    await database.initialize()
    try:
        yield database
    finally:
        await database.shutdown()


async def _seed_item(database: Database, **overrides: Any) -> str:
    async with database.session() as session:
        repository = SqlAlchemyItemRepository(session=session)
        item = await repository.create(payload=_item_payload(**overrides))
        item_id = item.id
        await session.commit()
        return item_id


def test_item_search_returns_empty_result_when_query_contains_fts_quote(
    tmp_path: Path,
) -> None:
    """Item search should treat quote characters as user input, not fail FTS syntax."""

    async def scenario() -> None:
        async with _temporary_database(tmp_path / "quote.db") as database:
            await _seed_item(database)

            async with database.session() as session:
                repository = SqlAlchemyItemRepository(session=session)

                results = await repository.search('"')

            assert results == []

    anyio.run(scenario)


def test_item_search_returns_empty_result_when_query_contains_fts_hyphen(
    tmp_path: Path,
) -> None:
    """Item search should treat hyphen characters as user input, not fail FTS syntax."""

    async def scenario() -> None:
        async with _temporary_database(tmp_path / "hyphen.db") as database:
            await _seed_item(database)

            async with database.session() as session:
                repository = SqlAlchemyItemRepository(session=session)

                results = await repository.search("-")

            assert results == []

    anyio.run(scenario)


def test_item_repository_persists_searches_updates_and_deletes_items(
    tmp_path: Path,
) -> None:
    """Repository should keep item rows and FTS rows consistent across lifecycle changes."""

    async def scenario() -> None:
        async with (
            _temporary_database(tmp_path / "items.db") as database,
            database.session() as session,
        ):
            repository = SqlAlchemyItemRepository(session=session)
            created = await repository.create(
                payload=_item_payload(
                    title="Deploy checklist",
                    content="Run migration checks before deploy",
                )
            )
            item_id = created.id

            assert (await repository.get(item_id)).title == "Deploy checklist"
            assert [item.id for item in await repository.search("migration")] == [
                item_id
            ]

            updated = await repository.update(
                item_id,
                payload=ItemUpdate(
                    values={"title": "Release checklist", "content": "Rollback notes"}
                ),
            )
            await session.commit()

            assert updated.title == "Release checklist"
            assert await repository.search("migration") == []
            assert [item.id for item in await repository.search("rollback")] == [
                item_id
            ]

            await repository.delete(item_id)
            await session.commit()

            assert await repository.get(item_id) is None
            assert await repository.search("rollback") == []

    anyio.run(scenario)


def test_item_repository_raises_not_found_when_mutating_missing_item(
    tmp_path: Path,
) -> None:
    """Repository should report missing rows with the shared not-found contract."""

    async def scenario() -> None:
        async with (
            _temporary_database(tmp_path / "missing.db") as database,
            database.session() as session,
        ):
            repository = SqlAlchemyItemRepository(session=session)

            missing_id = "00000000-0000-4000-8000-000000000000"

            with pytest.raises(NotFoundError, match=f"Item not found: {missing_id}"):
                await repository.update(
                    missing_id, payload=ItemUpdate(values={"title": "Missing"})
                )

            with pytest.raises(NotFoundError, match=f"Item not found: {missing_id}"):
                await repository.delete(missing_id)

    anyio.run(scenario)


def test_search_endpoint_returns_success_when_query_contains_fts_special_characters(
    tmp_path: Path,
) -> None:
    """Search endpoint should not expose server errors for FTS-special user input."""

    async def seed_database() -> Database:
        database = Database(
            database_url=f"sqlite+aiosqlite:///{tmp_path / 'api.db'}",
            create_schema=True,
        )
        await database.initialize()
        await _seed_item(database)
        return database

    database = anyio.run(seed_database)
    session_context = database.session()
    session = anyio.run(session_context.__aenter__)
    repository = SqlAlchemyItemRepository(session=session)
    item_service = ItemService(item_repo=repository)
    item_search_service = ItemSearchService(item_repo=repository)

    try:
        with (
            override_library_provider("item_service", item_service),
            override_library_provider("item_search_service", item_search_service),
        ):
            with TestClient(app, raise_server_exceptions=False) as client:
                quote_response = client.get("/retrieval/search", params={"q": '"'})
                hyphen_response = client.get("/retrieval/search", params={"q": "-"})
    finally:
        anyio.run(session_context.__aexit__, None, None, None)
        anyio.run(database.shutdown)

    assert quote_response.status_code == 200
    assert quote_response.json() == {
        "items": [],
        "total": 0,
        "limit": 20,
        "offset": 0,
    }
    assert hyphen_response.status_code == 200
    assert hyphen_response.json() == {
        "items": [],
        "total": 0,
        "limit": 20,
        "offset": 0,
    }


def test_item_fts_builds_safe_prefix_query_from_user_text() -> None:
    """FTS query building should tokenize user text and bind values separately."""
    query = build_item_fts_query('deploy-check "now"', ItemType.SKILL)

    assert query is not None
    assert query.parameters == {
        "query": '"deploy"* "check"* "now"*',
        "item_type": "SKILL",
    }


def test_item_fts_query_returns_none_when_query_has_no_tokens() -> None:
    """FTS query building should reject punctuation-only input before SQL execution."""
    assert build_item_fts_query('"-') is None
