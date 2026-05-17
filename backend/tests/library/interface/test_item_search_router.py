"""Behavior tests for thin library candidate search routes."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import anyio
from app.library.application.item_search_service import ItemSearchService
from app.library.application.item_service import ItemService
from app.library.domain.contracts.item_contracts import ItemCreate
from app.library.domain.event_enum.item_enums import (
    CreatedByType,
    ItemStatus,
    ItemType,
    SourceType,
)
from app.library.infrastructure.repositories.item_repository import (
    SqlAlchemyItemRepository,
)
from app.main import app
from app.shared.infrastructure.database import Database
from app.shared.types.extra_types import JSONValue
from fastapi.testclient import TestClient
from tests.shared.provider_overrides import override_library_provider


def _item_payload(
    *,
    title: str,
    item_type: ItemType = ItemType.SKILL,
    content: str,
    summary: str | None = None,
    tags: list[str] | None = None,
    status: ItemStatus = ItemStatus.ACTIVE,
    details: dict[str, JSONValue] | None = None,
) -> ItemCreate:
    now = datetime.now(UTC)
    return ItemCreate(
        item_type=item_type,
        title=title,
        summary=summary,
        content=content,
        category_id=None,
        tags=tags or [],
        status=status,
        source_type=SourceType.USER_CREATED,
        created_by_type=CreatedByType.USER,
        created_by_name="route-test",
        created_at=now,
        updated_at=now,
        details=details or {},
        is_archived=status is ItemStatus.ARCHIVED,
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
        await session.commit()
        return item.id


def test_library_search_returns_candidate_hits_without_content_when_query_matches(
    tmp_path: Path,
) -> None:
    """Library search should return candidate fields while selected get full-loads."""

    long_content = "pytest fixtures " + ("do not leak full content " * 400)

    async def seed_database() -> tuple[Database, str]:
        database = Database(
            database_url=f"sqlite+aiosqlite:///{tmp_path / 'candidate.db'}",
            create_schema=True,
        )
        await database.initialize()
        skill_id = await _seed_item(
            database,
            title="pytest fixture cleanup",
            content=long_content,
            summary="Clean up pytest fixtures safely.",
            tags=["pytest", "testing"],
            details={
                "purpose": "Clean up tests",
                "required_tools": ["pytest"],
                "risk_level": "LOW",
                "version": "1.0.0",
            },
        )
        await _seed_item(
            database,
            title="unrelated deployment notes",
            content="deploy release checklist",
            summary="Release operations",
            tags=["release"],
        )
        return database, skill_id

    database, skill_id = anyio.run(seed_database)
    session_context = database.session()
    session = anyio.run(session_context.__aenter__)
    repository = SqlAlchemyItemRepository(session=session)
    item_service = ItemService(item_repo=repository)
    search_service = ItemSearchService(item_repo=repository)

    try:
        with (
            override_library_provider("item_service", item_service),
            override_library_provider("item_search_service", search_service),
            TestClient(app, raise_server_exceptions=False) as client,
        ):
            search_response = client.get(
                "/library/search",
                params={
                    "q": "pytest",
                    "item_type": "SKILL",
                    "limit": "1",
                    "content_mode": "candidate",
                },
            )
            detail_response = client.get(f"/library/items/{skill_id}")
    finally:
        anyio.run(session_context.__aexit__, None, None, None)
        anyio.run(database.shutdown)

    assert search_response.status_code == 200
    payload = search_response.json()
    assert payload["total"] == 1
    assert payload["limit"] == 1
    assert payload["offset"] == 0
    assert len(payload["items"]) == 1
    hit = payload["items"][0]
    assert "content" not in hit
    assert hit == {
        "id": skill_id,
        "item_type": "SKILL",
        "title": "pytest fixture cleanup",
        "summary": "Clean up pytest fixtures safely.",
        "tags": ["pytest", "testing"],
        "status": "ACTIVE",
        "category_id": None,
        "score": hit["score"],
        "why_matched": ["title", "summary", "tags", "details"],
        "highlights": [
            "pytest fixture cleanup",
            "Clean up pytest fixtures safely.",
            "pytest",
        ],
        "details_preview": {
            "purpose": "Clean up tests",
            "required_tools": ["pytest"],
            "risk_level": "LOW",
            "version": "1.0.0",
        },
        "content_char_count": len(long_content),
        "updated_at": hit["updated_at"],
    }
    assert detail_response.status_code == 200
    assert detail_response.json()["content"] == long_content


def test_legacy_retrieval_search_uses_candidate_contract_for_special_characters(
    tmp_path: Path,
) -> None:
    """Legacy retrieval search should keep safe candidate semantics for broad search."""

    async def seed_database() -> Database:
        database = Database(
            database_url=f"sqlite+aiosqlite:///{tmp_path / 'legacy.db'}",
            create_schema=True,
        )
        await database.initialize()
        await _seed_item(
            database,
            title="Quote-safe search",
            content="quote and hyphen safe search terms",
            summary="Search helper",
            tags=["search"],
        )
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


def test_library_search_requires_explicit_content_field_for_body_matches(
    tmp_path: Path,
) -> None:
    """Default search should not match content body unless content is requested."""

    async def seed_database() -> Database:
        database = Database(
            database_url=f"sqlite+aiosqlite:///{tmp_path / 'fields.db'}",
            create_schema=True,
        )
        await database.initialize()
        await _seed_item(
            database,
            title="Metadata only title",
            content="bodyonlymarker appears only in the long body",
            summary="Metadata summary",
            tags=["metadata"],
            details={
                "body": "detailbodymarker appears only in detail body",
                "purpose": "metadata-marker",
            },
        )
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
            default_response = client.get(
                "/library/search",
                params={"q": "bodyonlymarker"},
            )
            content_response = client.get(
                "/library/search",
                params={"q": "bodyonlymarker", "search_fields": "content"},
            )
            metadata_content_response = client.get(
                "/library/search",
                params={
                    "q": "bodyonlymarker",
                    "strategy": "metadata",
                    "search_fields": "content",
                },
            )
            default_detail_response = client.get(
                "/library/search",
                params={"q": "detailbodymarker"},
            )
            explicit_detail_body_response = client.get(
                "/library/search",
                params={"q": "detailbodymarker", "search_fields": "content"},
            )
            metadata_detail_response = client.get(
                "/library/search",
                params={"q": "metadata-marker"},
            )
    finally:
        anyio.run(session_context.__aexit__, None, None, None)
        anyio.run(database.shutdown)

    assert default_response.status_code == 200
    assert default_response.json()["total"] == 0
    assert content_response.status_code == 200
    content_payload = content_response.json()
    assert content_payload["total"] == 1
    assert content_payload["items"][0]["why_matched"] == ["content_body"]
    assert metadata_content_response.status_code == 400
    assert default_detail_response.status_code == 200
    assert default_detail_response.json()["total"] == 0
    assert explicit_detail_body_response.status_code == 200
    assert explicit_detail_body_response.json()["total"] == 1
    assert metadata_detail_response.status_code == 200
    assert metadata_detail_response.json()["total"] == 1
