"""Router contract tests for Context Vault endpoints."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import anyio
from app.main import app
from app.memory.application.context_service import ContextService
from app.memory.domain.event_enum.context_enums import (
    ContextKind,
    ContextScope,
    ContextSourceType,
)
from app.memory.infrastructure.models.context_models import (
    ContextAccessEventORM,
    ContextChunkORM,
    ContextORM,
)
from app.memory.infrastructure.repositories.context_repository import (
    SqlAlchemyContextRepository,
)
from app.shared.infrastructure.database import Database
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from tests.memory.context_seed import seed_context
from tests.shared.provider_overrides import override_library_provider


def _context_payload() -> dict[str, object]:
    return {
        "kind": "HANDOFF",
        "title": "API handoff",
        "summary": "API saves and recalls context.",
        "content": """# API handoff

## Summary
API saves and recalls context.

## Current State
- Context API is under test.

## Next Actions
1. Add CLI.

## Restore Prompt
Continue from the API context.
""",
        "project": "alexandria-hermes",
        "source_agent": "Hermes",
        "tags": ["api", "handoff"],
    }


async def _open_context_service(
    path: Path,
) -> tuple[Database, Any, AsyncSession, ContextService]:
    database = Database(database_url=f"sqlite+aiosqlite:///{path}", create_schema=True)
    await database.initialize()
    session_context = database.session()
    session = await session_context.__aenter__()
    service = ContextService(repository=SqlAlchemyContextRepository(session=session))
    return database, session_context, session, service


async def _close_context_service(
    database: Database,
    session_context: Any,
    session: AsyncSession,
) -> None:
    await session.commit()
    await session_context.__aexit__(None, None, None)
    await database.shutdown()


async def _seed_api_context(
    session: AsyncSession,
    title: str = "API handoff",
    summary: str = "API saves and recalls context.",
    content: str | None = None,
    project: str | None = "alexandria-hermes",
    scope: ContextScope = ContextScope.PROJECT,
    user_id: str | None = None,
    source_type: ContextSourceType = ContextSourceType.AGENT,
    restore_prompt: str | None = "Continue from the API context.",
) -> str:
    payload = _context_payload()
    context = await seed_context(
        session,
        kind=ContextKind.HANDOFF,
        title=title,
        summary=summary,
        content=str(payload["content"]) if content is None else content,
        project=project,
        scope=scope,
        user_id=user_id,
        source_agent="Hermes",
        source_type=source_type,
        tags=["api", "handoff"],
        restore_prompt=restore_prompt,
    )
    await session.commit()
    return context.id


async def _set_context_dates(
    session: AsyncSession,
    context_id: str,
    created_at: datetime,
    updated_at: datetime,
) -> None:
    model = await session.get(ContextORM, context_id)
    assert model is not None
    model.created_at = created_at
    model.updated_at = updated_at
    await session.commit()


async def _context_persistence_counts(
    session: AsyncSession,
    context_id: str,
) -> dict[str, int]:
    context_count = await session.scalar(
        select(func.count()).select_from(ContextORM).where(ContextORM.id == context_id)
    )
    chunk_count = await session.scalar(
        select(func.count())
        .select_from(ContextChunkORM)
        .where(ContextChunkORM.context_id == context_id)
    )
    access_event_count = await session.scalar(
        select(func.count())
        .select_from(ContextAccessEventORM)
        .where(ContextAccessEventORM.context_id == context_id)
    )
    return {
        "contexts": int(context_count or 0),
        "chunks": int(chunk_count or 0),
        "access_events": int(access_event_count or 0),
    }


def test_context_api_filters_list_by_created_and_updated_dates(tmp_path: Path) -> None:
    """Context list route should accept created/updated date-range filters."""

    database, session_context, session, service = anyio.run(
        _open_context_service, tmp_path / "context-api-date-filters.db"
    )
    try:
        older_id = anyio.run(_seed_api_context, session, "Older API handoff")
        inside_id = anyio.run(_seed_api_context, session, "Inside API handoff")
        newer_id = anyio.run(_seed_api_context, session, "Newer API handoff")
        anyio.run(
            _set_context_dates,
            session,
            older_id,
            datetime(2026, 5, 17, 10, 0, tzinfo=UTC),
            datetime(2026, 5, 17, 11, 0, tzinfo=UTC),
        )
        anyio.run(
            _set_context_dates,
            session,
            inside_id,
            datetime(2026, 5, 18, 10, 0, tzinfo=UTC),
            datetime(2026, 5, 18, 11, 0, tzinfo=UTC),
        )
        anyio.run(
            _set_context_dates,
            session,
            newer_id,
            datetime(2026, 5, 19, 10, 0, tzinfo=UTC),
            datetime(2026, 5, 19, 11, 0, tzinfo=UTC),
        )
        with (
            override_library_provider("context_service", service),
            TestClient(app, raise_server_exceptions=False) as client,
        ):
            created_response = client.get(
                "/memory/contexts",
                params={
                    "created_after": "2026-05-18T00:00:00.000Z",
                    "created_before": "2026-05-18T23:59:59.999Z",
                },
            )
            updated_response = client.get(
                "/memory/contexts",
                params={
                    "updated_after": "2026-05-18T00:00:00.000Z",
                    "updated_before": "2026-05-18T23:59:59.999Z",
                },
            )
            naive_response = client.get(
                "/memory/contexts",
                params={"created_after": "2026-05-18T00:00:00"},
            )
    finally:
        anyio.run(_close_context_service, database, session_context, session)

    assert created_response.status_code == 200
    assert [item["id"] for item in created_response.json()["items"]] == [inside_id]
    assert updated_response.status_code == 200
    assert [item["id"] for item in updated_response.json()["items"]] == [inside_id]
    assert naive_response.status_code == 422


def test_context_api_hard_deletes_context_rows_chunks_access_events_and_search_index(
    tmp_path: Path,
) -> None:
    """Context delete should remove durable rows and retrieval traces."""
    database, session_context, session, service = anyio.run(
        _open_context_service, tmp_path / "context-api-delete.db"
    )
    try:
        context_id = anyio.run(_seed_api_context, session)
        with (
            override_library_provider("context_service", service),
            TestClient(app, raise_server_exceptions=False) as client,
        ):
            access_response = client.post(
                f"/memory/contexts/{context_id}/access-events",
                json={
                    "actor_name": "Alexandria UI",
                    "actor_type": "UI",
                    "access_method": "DETAIL_VIEW",
                    "source_surface": "context-detail",
                },
            )
            before_search_response = client.post(
                "/memory/contexts/retrieval/search",
                json={"query": "API saves recalls", "strategy": "HYBRID"},
            )
            delete_response = client.delete(f"/memory/contexts/{context_id}")
            after_get_response = client.get(f"/memory/contexts/{context_id}")
            after_list_response = client.get(
                "/memory/contexts", params={"include_archived": "true"}
            )
            after_search_response = client.post(
                "/memory/contexts/retrieval/search",
                json={"query": "API saves recalls", "strategy": "HYBRID"},
            )
            counts = anyio.run(_context_persistence_counts, session, context_id)
    finally:
        anyio.run(_close_context_service, database, session_context, session)

    assert access_response.status_code == 201
    assert before_search_response.status_code == 200
    assert context_id in before_search_response.json()["context_pack"]
    assert delete_response.status_code == 204
    assert delete_response.content == b""
    assert after_get_response.status_code == 404
    assert after_list_response.status_code == 200
    assert after_list_response.json()["total"] == 0
    assert after_search_response.status_code == 200
    assert after_search_response.json()["matches"] == []
    assert counts == {"contexts": 0, "chunks": 0, "access_events": 0}


def test_context_api_lists_searches_accesses_and_archives_seeded_context(
    tmp_path: Path,
) -> None:
    """Context API should expose the archive-first recall lifecycle for indexed rows."""

    database, session_context, session, service = anyio.run(
        _open_context_service, tmp_path / "context-api.db"
    )
    try:
        context_id = anyio.run(_seed_api_context, session)
        with (
            override_library_provider("context_service", service),
            TestClient(app, raise_server_exceptions=False) as client,
        ):
            list_response = client.get(
                "/memory/contexts", params={"project": "alexandria-hermes"}
            )
            get_response = client.get(f"/memory/contexts/{context_id}")
            chunks_response = client.get(f"/memory/contexts/{context_id}/chunks")
            search_response = client.post(
                "/memory/contexts/retrieval/search",
                json={"query": "API saves recalls", "strategy": "HYBRID"},
            )
            access_response = client.post(f"/memory/contexts/{context_id}/access")
            access_event_response = client.post(
                f"/memory/contexts/{context_id}/access-events",
                json={
                    "actor_name": "Alexandria UI",
                    "actor_type": "UI",
                    "access_method": "DETAIL_VIEW",
                    "source_surface": "context-detail",
                },
            )
            access_events_response = client.get(
                f"/memory/contexts/{context_id}/access-events",
                params={"limit": 5},
            )
            archive_response = client.post(f"/memory/contexts/{context_id}/archive")
            rag_response = client.get("/memory/contexts/rag/status")
            reindex_response = client.post("/memory/contexts/retrieval/reindex")
    finally:
        anyio.run(_close_context_service, database, session_context, session)

    assert list_response.status_code == 200
    assert list_response.json()["total"] == 1
    assert get_response.status_code == 200
    assert get_response.json()["id"] == context_id
    assert get_response.json()["restore_prompt"] == "Continue from the API context."
    assert get_response.json()["source_type"] == "AGENT"
    assert chunks_response.status_code == 200
    assert chunks_response.json()[0]["context_id"] == context_id
    assert search_response.status_code == 200
    assert search_response.json()["effective_strategy"] == "FTS_ONLY"
    assert context_id in search_response.json()["context_pack"]
    assert access_response.status_code == 200
    assert access_response.json()["access_count"] == 1
    assert access_event_response.status_code == 201
    assert access_event_response.json()["actor_type"] == "UI"
    assert access_event_response.json()["access_method"] == "DETAIL_VIEW"
    assert access_events_response.status_code == 200
    assert len(access_events_response.json()) == 2
    assert {event["source_surface"] for event in access_events_response.json()} == {
        "context-detail"
    }
    assert archive_response.status_code == 200
    assert archive_response.json()["is_archived"] is True
    assert rag_response.status_code == 200
    assert rag_response.json()["fts"] == "HEALTHY"
    assert reindex_response.status_code == 200
    assert reindex_response.json()["updated"] == 0


def test_context_api_filters_recall_by_memory_scope(tmp_path: Path) -> None:
    """Scoped recall should return only contexts from requested memory lanes."""

    database, session_context, session, service = anyio.run(
        _open_context_service, tmp_path / "scope-recall.db"
    )
    try:
        scoped_content = "# Scoped recall\n\n## Summary\nScoped recall token."
        anyio.run(
            _seed_api_context,
            session,
            "Project scoped recall",
            "Scoped recall token.",
            scoped_content,
            "alexandria-hermes",
            ContextScope.PROJECT,
        )
        user_context_id = anyio.run(
            _seed_api_context,
            session,
            "User scoped recall",
            "Scoped recall token.",
            scoped_content,
            "alexandria-hermes",
            ContextScope.USER,
            "ha_nori",
        )
        with (
            override_library_provider("context_service", service),
            TestClient(app, raise_server_exceptions=False) as client,
        ):
            search_response = client.post(
                "/memory/contexts/retrieval/search",
                json={"query": "Scoped recall token", "include_scopes": ["USER"]},
            )
    finally:
        anyio.run(_close_context_service, database, session_context, session)

    assert search_response.status_code == 200
    matches = search_response.json()["matches"]
    assert {match["context"]["id"] for match in matches} == {user_context_id}
    assert search_response.json()["recall_scopes"] == ["USER"]


def test_context_api_write_routes_are_not_exposed() -> None:
    """Context Vault capture and compact-save routes should be absent."""
    with TestClient(app, raise_server_exceptions=False) as client:
        capture_response = client.post(
            "/memory/contexts/capture", json=_context_payload()
        )
        compact_response = client.post(
            "/memory/contexts/prepare-compact",
            json={"current_goal": "Context API"},
        )

    assert capture_response.status_code in {404, 405}
    assert compact_response.status_code in {404, 405}
