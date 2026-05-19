"""Router contract tests for Context Vault endpoints."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import anyio
from app.main import app
from app.memory.application.context_service import ContextService
from app.memory.infrastructure.repositories.context_repository import (
    SqlAlchemyContextRepository,
)
from app.shared.infrastructure.database import Database
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession
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


def test_context_api_captures_lists_searches_accesses_and_archives(
    tmp_path: Path,
) -> None:
    """Context API should expose the agent-capture archive-first recall lifecycle."""

    database, session_context, session, service = anyio.run(
        _open_context_service, tmp_path / "context-api.db"
    )
    try:
        with (
            override_library_provider("context_service", service),
            TestClient(app, raise_server_exceptions=False) as client,
        ):
            create_response = client.post(
                "/memory/contexts/capture", json=_context_payload()
            )
            context_id = create_response.json()["id"]
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

    assert create_response.status_code == 201
    assert create_response.json()["restore_prompt"] == "Continue from the API context."
    assert create_response.json()["source_type"] == "AGENT"
    assert list_response.status_code == 200
    assert list_response.json()["total"] == 1
    assert get_response.status_code == 200
    assert get_response.json()["id"] == context_id
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
        base_payload = _context_payload() | {
            "title": "Scoped recall",
            "summary": "Scoped recall token.",
            "content": "# Scoped recall\n\n## Summary\nScoped recall token.",
        }
        with (
            override_library_provider("context_service", service),
            TestClient(app, raise_server_exceptions=False) as client,
        ):
            project_response = client.post(
                "/memory/contexts/capture",
                json=base_payload | {"scope": "PROJECT"},
            )
            user_response = client.post(
                "/memory/contexts/capture",
                json=base_payload | {"scope": "USER", "user_id": "ha_nori"},
            )
            search_response = client.post(
                "/memory/contexts/retrieval/search",
                json={"query": "Scoped recall token", "include_scopes": ["USER"]},
            )
    finally:
        anyio.run(_close_context_service, database, session_context, session)

    assert project_response.status_code == 201
    assert user_response.status_code == 201
    assert search_response.status_code == 200
    matches = search_response.json()["matches"]
    assert {match["context"]["id"] for match in matches} == {user_response.json()["id"]}
    assert search_response.json()["recall_scopes"] == ["USER"]


def test_context_api_prepare_compact_saves_structured_handoff(tmp_path: Path) -> None:
    """Prepare-compact should turn structured state into a COMPACT context."""

    database, session_context, session, service = anyio.run(
        _open_context_service, tmp_path / "prepare-compact.db"
    )
    try:
        with (
            override_library_provider("context_service", service),
            TestClient(app, raise_server_exceptions=False) as client,
        ):
            response = client.post(
                "/memory/contexts/prepare-compact",
                json={
                    "project": "alexandria-hermes",
                    "source_agent": "Hermes",
                    "current_goal": "Context API",
                    "completed": ["storage"],
                    "in_progress": ["router"],
                    "key_decisions": ["Context Pack default"],
                    "next_actions": ["CLI"],
                    "risks": ["vector degraded"],
                },
            )
    finally:
        anyio.run(_close_context_service, database, session_context, session)

    assert response.status_code == 201
    assert response.json()["kind"] == "COMPACT"
    assert response.json()["project"] == "alexandria-hermes"
    assert response.json()["source_type"] == "AGENT"
    assert "Context Pack default" in response.json()["content"]


def test_context_api_captures_agent_owned_harness_without_library_route(
    tmp_path: Path,
) -> None:
    """Harness capture should store execution memory without library CRUD."""

    database, session_context, session, service = anyio.run(
        _open_context_service, tmp_path / "harness-capture.db"
    )
    try:
        with (
            override_library_provider("context_service", service),
            TestClient(app, raise_server_exceptions=False) as client,
        ):
            create_response = client.post(
                "/memory/contexts/harnesses/capture",
                json={
                    "task_goal": "Remove workflow surface",
                    "summary": "Reusable execution trace for removing a product surface.",
                    "project": "alexandria-hermes",
                    "source_agent": "Hermes",
                    "environment": "local pytest",
                    "trigger_context": "WORKFLOW was unused manual CRUD.",
                    "steps": ["Add pruning contract", "Remove router"],
                    "commands": ["uv run --no-editable pytest -q tests/library"],
                    "tests": ["workflow pruning contract"],
                    "failures": ["Initial route still exposed"],
                    "fixes": ["Removed router registration"],
                    "artifacts": [
                        "backend/tests/library/interface/test_workflow_pruning_contract.py"
                    ],
                    "reusable_procedure": "Write a pruning contract, remove the public route, then run targeted tests.",
                    "recall_keywords": ["workflow-removal", "surface-pruning"],
                    "safety_notes": ["Do not add a replacement human CRUD surface."],
                    "metadata": {
                        "harness": {"task_goal": "spoofed"},
                        "caller_note": "preserve caller metadata",
                    },
                },
            )
            search_response = client.post(
                "/memory/contexts/retrieval/search",
                json={
                    "query": "surface pruning workflow removal",
                    "kind": "HARNESS",
                    "include_scopes": ["PROJECT"],
                },
            )

    finally:
        anyio.run(_close_context_service, database, session_context, session)

    library_harness_paths = [
        path for path in app.openapi()["paths"] if path.startswith("/library/harness")
    ]
    body = create_response.json()
    assert create_response.status_code == 201
    assert body["kind"] == "HARNESS"
    assert body["source_type"] == "AGENT"
    assert body["importance"] == "HIGH"
    assert body["metadata"]["harness"]["task_goal"] == "Remove workflow surface"
    assert body["metadata"]["harness"]["recall_keywords"] == [
        "workflow-removal",
        "surface-pruning",
    ]
    assert body["metadata"]["caller_note"] == "preserve caller metadata"
    assert "## Reusable Procedure" in body["content"]
    assert "Recall this HARNESS" in body["restore_prompt"]
    assert search_response.status_code == 200
    assert search_response.json()["matches"][0]["context"]["id"] == body["id"]
    assert library_harness_paths == []


def test_generic_context_capture_rejects_harness_kind(tmp_path: Path) -> None:
    """Generic context capture should not bypass generated HARNESS metadata."""

    database, session_context, session, service = anyio.run(
        _open_context_service, tmp_path / "generic-harness-reject.db"
    )
    try:
        with (
            override_library_provider("context_service", service),
            TestClient(app, raise_server_exceptions=False) as client,
        ):
            response = client.post(
                "/memory/contexts/capture",
                json=_context_payload()
                | {
                    "kind": "HARNESS",
                    "metadata": {"harness": {"task_goal": "spoofed"}},
                },
            )
    finally:
        anyio.run(_close_context_service, database, session_context, session)

    assert response.status_code == 400
    assert response.json()["detail"] == (
        "HARNESS contexts must be captured through /memory/contexts/harnesses/capture"
    )


def test_context_api_accepts_imported_source_type(tmp_path: Path) -> None:
    """Imported context should use the canonical IMPORTED source category."""

    database, session_context, session, service = anyio.run(
        _open_context_service, tmp_path / "imported-source.db"
    )
    try:
        payload = _context_payload() | {"source_type": "IMPORTED"}
        with (
            override_library_provider("context_service", service),
            TestClient(app, raise_server_exceptions=False) as client,
        ):
            response = client.post("/memory/contexts/capture", json=payload)
    finally:
        anyio.run(_close_context_service, database, session_context, session)

    assert response.status_code == 201
    assert response.json()["source_type"] == "IMPORTED"


def test_context_api_returns_validation_error_for_invalid_kind(tmp_path: Path) -> None:
    """Invalid enum-like input should be rejected at the schema boundary."""

    database, session_context, session, service = anyio.run(
        _open_context_service, tmp_path / "invalid-kind.db"
    )
    try:
        payload = _context_payload() | {"kind": "NOTE"}
        with (
            override_library_provider("context_service", service),
            TestClient(app, raise_server_exceptions=False) as client,
        ):
            response = client.post("/memory/contexts/capture", json=payload)
    finally:
        anyio.run(_close_context_service, database, session_context, session)

    assert response.status_code == 422
    assert response.json()["detail"][0]["loc"] == ["body", "kind"]
