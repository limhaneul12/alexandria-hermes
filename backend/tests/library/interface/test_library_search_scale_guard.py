"""Regression tests for broad candidate search response size."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from pathlib import Path

import anyio
from app.library.application.item_search_service import ItemSearchService
from app.library.domain.contracts.item_contracts import ItemCreate
from app.library.domain.event_enum.item_enums import (
    CreatedByType,
    ItemStatus,
    ItemType,
    SourceType,
)
from app.library.infrastructure.repositories.category_repository import (
    SqlAlchemyCategoryRepository,
)
from app.library.infrastructure.repositories.item_repository import (
    SqlAlchemyItemRepository,
)
from app.main import app
from app.shared.infrastructure.database import Database
from app.shared.serialization.orjson_codec import dumps_json
from fastapi.testclient import TestClient
from tests.shared.provider_overrides import override_library_provider


@asynccontextmanager
async def _temporary_database(path: Path) -> AsyncIterator[Database]:
    database = Database(database_url=f"sqlite+aiosqlite:///{path}", create_schema=True)
    await database.initialize()
    try:
        yield database
    finally:
        await database.shutdown()


def _item_payload(index: int, *, item_type: ItemType, tags: list[str]) -> ItemCreate:
    now = datetime.now(UTC)
    details = (
        {
            "prompt_kind": "DEVELOPER" if index % 2 == 0 else "SYSTEM",
            "prompt_domain": "DEVELOPMENT",
            "prompt_task_type": "CODE_REVIEW",
            "content_format": "MARKDOWN",
        }
        if item_type is ItemType.PROMPT
        else {"required_tools": ["pytest"], "risk_level": "LOW"}
    )
    return ItemCreate(
        item_type=item_type,
        title=f"needle candidate {index}",
        summary="Short searchable summary",
        content="needle " + ("long body must not be returned " * 600),
        category_id=None,
        tags=tags,
        status=ItemStatus.ACTIVE,
        source_type=SourceType.USER_CREATED,
        created_by_type=CreatedByType.USER,
        created_by_name="scale-test",
        created_at=now,
        updated_at=now,
        details=details,
        is_archived=False,
    )


def _categorized_item_payload(
    index: int,
    *,
    category_id: str,
) -> ItemCreate:
    now = datetime.now(UTC)
    return ItemCreate(
        item_type=ItemType.SKILL,
        title=f"needle category candidate {index}",
        summary="Category scoped searchable summary",
        content="needle " + ("category body must not be returned " * 300),
        category_id=category_id,
        tags=["category-scope"],
        status=ItemStatus.ACTIVE,
        source_type=SourceType.USER_CREATED,
        created_by_type=CreatedByType.USER,
        created_by_name="scale-test",
        created_at=now,
        updated_at=now,
        details={"required_tools": ["pytest"], "risk_level": "LOW"},
        is_archived=False,
    )


def _dated_item_payload(title: str, *, updated_at: datetime) -> ItemCreate:
    return ItemCreate(
        item_type=ItemType.SKILL,
        title=title,
        summary="Date scoped searchable summary",
        content="needle date scoped body",
        category_id=None,
        tags=["date-scope"],
        status=ItemStatus.ACTIVE,
        source_type=SourceType.USER_CREATED,
        created_by_type=CreatedByType.USER,
        created_by_name="scale-test",
        created_at=updated_at,
        updated_at=updated_at,
        details={"required_tools": ["pytest"], "risk_level": "LOW"},
        is_archived=False,
    )


def test_library_search_payload_size_is_bounded_when_many_long_items_match(
    tmp_path: Path,
) -> None:
    """Broad search should paginate candidates without returning matched content."""

    async def seed_database() -> Database:
        database = Database(
            database_url=f"sqlite+aiosqlite:///{tmp_path / 'scale.db'}",
            create_schema=True,
        )
        await database.initialize()
        async with database.session() as session:
            repository = SqlAlchemyItemRepository(session=session)
            for index in range(30):
                item_type = ItemType.PROMPT if index % 3 == 0 else ItemType.SKILL
                tags = ["code-review"] if item_type is ItemType.PROMPT else ["pytest"]
                await repository.create(
                    payload=_item_payload(index, item_type=item_type, tags=tags)
                )
            await session.commit()
        return database

    database = anyio.run(seed_database)
    session_context = database.session()
    session = anyio.run(session_context.__aenter__)
    search_service = ItemSearchService(
        item_repo=SqlAlchemyItemRepository(session=session)
    )

    try:
        with (
            override_library_provider("item_search_service", search_service),
            TestClient(app, raise_server_exceptions=False) as client,
        ):
            response = client.get(
                "/library/search",
                params={"q": "needle", "limit": "5", "offset": "5"},
            )
            prompt_response = client.get(
                "/library/search",
                params={
                    "q": "needle",
                    "item_type": "PROMPT",
                    "prompt_kind": "DEVELOPER",
                    "tags_any": "code-review",
                    "limit": "20",
                },
            )
    finally:
        anyio.run(session_context.__aexit__, None, None, None)
        anyio.run(database.shutdown)

    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 30
    assert payload["limit"] == 5
    assert payload["offset"] == 5
    assert len(payload["items"]) == 5
    assert all("content" not in item for item in payload["items"])
    assert len(dumps_json(payload)) < 12_000

    assert prompt_response.status_code == 200
    prompt_payload = prompt_response.json()
    assert prompt_payload["total"] == 5
    assert {
        item["details_preview"]["prompt_kind"] for item in prompt_payload["items"]
    } == {"DEVELOPER"}


def test_library_search_applies_descendant_category_filter_before_pagination(
    tmp_path: Path,
) -> None:
    """Category search should not filter after a capped global candidate page."""

    async def seed_database() -> tuple[Database, str]:
        database = Database(
            database_url=f"sqlite+aiosqlite:///{tmp_path / 'category.db'}",
            create_schema=True,
        )
        await database.initialize()
        async with database.session() as session:
            category_repository = SqlAlchemyCategoryRepository(session=session)
            item_repository = SqlAlchemyItemRepository(session=session)
            parent = await category_repository.create(name="Parent")
            child = await category_repository.create(name="Child", parent_id=parent.id)
            for index in range(12):
                await item_repository.create(
                    payload=_item_payload(
                        index,
                        item_type=ItemType.SKILL,
                        tags=["outside-category"],
                    )
                )
            await item_repository.create(
                payload=_categorized_item_payload(99, category_id=child.id)
            )
            await session.commit()
        return database, parent.id

    database, parent_id = anyio.run(seed_database)
    session_context = database.session()
    session = anyio.run(session_context.__aenter__)
    search_service = ItemSearchService(
        item_repo=SqlAlchemyItemRepository(session=session)
    )

    try:
        with (
            override_library_provider("item_search_service", search_service),
            TestClient(app, raise_server_exceptions=False) as client,
        ):
            response = client.get(
                "/library/search",
                params={
                    "q": "needle",
                    "category_id": parent_id,
                    "include_descendant_categories": "true",
                    "limit": "1",
                },
            )
    finally:
        anyio.run(session_context.__aexit__, None, None, None)
        anyio.run(database.shutdown)

    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 1
    assert len(payload["items"]) == 1
    assert payload["items"][0]["title"] == "needle category candidate 99"


def test_library_search_filters_candidates_by_updated_date_range(
    tmp_path: Path,
) -> None:
    """Updated date filters should be applied before pagination."""

    async def seed_database() -> Database:
        database = Database(
            database_url=f"sqlite+aiosqlite:///{tmp_path / 'dates.db'}",
            create_schema=True,
        )
        await database.initialize()
        async with database.session() as session:
            item_repository = SqlAlchemyItemRepository(session=session)
            for title, updated_at in [
                ("needle older item", datetime(2026, 5, 17, 12, tzinfo=UTC)),
                ("needle target item", datetime(2026, 5, 18, 12, tzinfo=UTC)),
                ("needle newer item", datetime(2026, 5, 19, 12, tzinfo=UTC)),
            ]:
                await item_repository.create(
                    payload=_dated_item_payload(title, updated_at=updated_at)
                )
            await session.commit()
        return database

    database = anyio.run(seed_database)
    session_context = database.session()
    session = anyio.run(session_context.__aenter__)
    search_service = ItemSearchService(
        item_repo=SqlAlchemyItemRepository(session=session)
    )

    try:
        with (
            override_library_provider("item_search_service", search_service),
            TestClient(app, raise_server_exceptions=False) as client,
        ):
            response = client.get(
                "/library/search",
                params={
                    "q": "needle",
                    "updated_after": "2026-05-18T00:00:00.000Z",
                    "updated_before": "2026-05-18T23:59:59.999Z",
                    "limit": "10",
                },
            )
    finally:
        anyio.run(session_context.__aexit__, None, None, None)
        anyio.run(database.shutdown)

    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 1
    assert [item["title"] for item in payload["items"]] == ["needle target item"]
