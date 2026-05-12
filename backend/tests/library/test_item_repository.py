"""Behavior tests for library item repository search contracts."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import anyio
import pytest
from fastapi.testclient import TestClient

from app.library.application.item_service import ItemService
from app.library.domain.entities.enums import (
    CreatedByType,
    ItemStatus,
    ItemType,
    SourceType,
)
from app.library.infrastructure.repositories.item_repository import (
    SqlAlchemyItemRepository,
)
from app.library.interface.routers.dependencies import get_item_service
from app.main import app
from app.shared.exceptions import NotFoundError
from app.shared.infrastructure.database import Database
from app.shared.types.extra_types import JSONValue


def _item_payload(
    *,
    title: str = "Quote-ready search skill",
    item_type: ItemType = ItemType.SKILL,
    content: str = "Use quote and hyphen safe search terms.",
    summary: str | None = "Search helper",
    tags: list[str] | None = None,
    details: dict[str, JSONValue] | None = None,
) -> dict[str, JSONValue]:
    now = datetime.now(UTC)
    return {
        "item_type": item_type.value,
        "title": title,
        "summary": summary,
        "content": content,
        "category_id": None,
        "tags": tags or ["search"],
        "status": ItemStatus.ACTIVE.value,
        "source_type": SourceType.USER_CREATED.value,
        "created_by_type": CreatedByType.USER.value,
        "created_by_name": "test-user",
        "created_at": now,
        "updated_at": now,
        "details": details or {},
        "is_archived": False,
    }


@asynccontextmanager
async def _temporary_database(path: Path) -> AsyncIterator[Database]:
    database = Database(database_url=f"sqlite+aiosqlite:///{path}")
    await database.initialize()
    try:
        yield database
    finally:
        await database.shutdown()


async def _seed_item(database: Database, **overrides: Any) -> int:
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
        async with _temporary_database(tmp_path / "items.db") as database:
            async with database.session() as session:
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
                    payload={"title": "Release checklist", "content": "Rollback notes"},
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
        async with _temporary_database(tmp_path / "missing.db") as database:
            async with database.session() as session:
                repository = SqlAlchemyItemRepository(session=session)

                with pytest.raises(NotFoundError, match="Item not found: 404"):
                    await repository.update(404, payload={"title": "Missing"})

                with pytest.raises(NotFoundError, match="Item not found: 404"):
                    await repository.delete(404)

    anyio.run(scenario)


def test_search_endpoint_returns_success_when_query_contains_fts_special_characters(
    tmp_path: Path,
) -> None:
    """Search endpoint should not expose server errors for FTS-special user input."""

    async def seed_database() -> Database:
        database = Database(database_url=f"sqlite+aiosqlite:///{tmp_path / 'api.db'}")
        await database.initialize()
        await _seed_item(database)
        return database

    database = anyio.run(seed_database)

    async def override_item_service() -> AsyncIterator[ItemService]:
        async with database.session() as session:
            yield ItemService(item_repo=SqlAlchemyItemRepository(session=session))

    app.dependency_overrides[get_item_service] = override_item_service
    try:
        with TestClient(app, raise_server_exceptions=False) as client:
            quote_response = client.get("/search", params={"q": '"'})
            hyphen_response = client.get("/search", params={"q": "-"})
    finally:
        app.dependency_overrides.pop(get_item_service, None)
        anyio.run(database.shutdown)

    assert quote_response.status_code == 200
    assert quote_response.json() == []
    assert hyphen_response.status_code == 200
    assert hyphen_response.json() == []
