"""Memory Compact router contract tests."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import anyio
from app.main import app
from app.memory.application.memory_compact_service import MemoryCompactService
from app.memory.infrastructure.models.memory_compact_models import (
    MemoryCompactORM,
    MemoryCompactSourceRefORM,
)
from app.memory.infrastructure.repositories.memory_compact_repository import (
    SqlAlchemyMemoryCompactRepository,
)
from app.shared.infrastructure.database import Database
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from tests.shared.provider_overrides import override_library_provider


async def _open_service(
    path: Path,
) -> tuple[Database, Any, AsyncSession, MemoryCompactService]:
    database = Database(database_url=f"sqlite+aiosqlite:///{path}", create_schema=True)
    await database.initialize()
    session_context = database.session()
    session = await session_context.__aenter__()
    service = MemoryCompactService(
        repository=SqlAlchemyMemoryCompactRepository(session=session)
    )
    return database, session_context, session, service


async def _close_service(
    database: Database,
    session_context: Any,
    session: AsyncSession,
) -> None:
    await session.commit()
    await session_context.__aexit__(None, None, None)
    await database.shutdown()


async def _compact_persistence_counts(
    session: AsyncSession,
    compact_id: str,
) -> dict[str, int]:
    compact_count = await session.scalar(
        select(func.count())
        .select_from(MemoryCompactORM)
        .where(MemoryCompactORM.id == compact_id)
    )
    source_ref_count = await session.scalar(
        select(func.count())
        .select_from(MemoryCompactSourceRefORM)
        .where(MemoryCompactSourceRefORM.compact_id == compact_id)
    )
    return {
        "compacts": int(compact_count or 0),
        "source_refs": int(source_ref_count or 0),
    }


def _payload(
    status: str = "CURRENT",
    *,
    covered_from: str = "2026-05-01T00:00:00Z",
    covered_to: str = "2026-05-10T00:00:00Z",
    source_id: str = "ctx-1",
) -> dict[str, object]:
    return {
        "project": "alexandria-hermes",
        "covered_from": covered_from,
        "covered_to": covered_to,
        "markdown_body": (
            f"## {covered_from[:10]} to {covered_to[:10]}\nDurable Memory Compact."
        ),
        "status": status,
        "source_refs": [
            {
                "source_type": "CONTEXT",
                "source_id": source_id,
                "title": "Context source",
                "detail_path": f"/memory/contexts/{source_id}",
            }
        ],
    }


def test_memory_compact_api_hard_deletes_compact_and_source_refs(
    tmp_path: Path,
) -> None:
    """Memory Compact delete should remove the artifact and its source refs."""
    database, session_context, session, service = anyio.run(
        _open_service, tmp_path / "compact-api-delete.db"
    )
    try:
        with (
            override_library_provider("memory_compact_service", service),
            TestClient(app, raise_server_exceptions=False) as client,
        ):
            create_response = client.post("/memory/compacts", json=_payload())
            compact_id = create_response.json()["id"]
            delete_response = client.delete(f"/memory/compacts/{compact_id}")
            get_response = client.get(f"/memory/compacts/{compact_id}")
            list_response = client.get(
                "/memory/compacts", params={"project": "alexandria-hermes"}
            )
            current_response = client.get(
                "/memory/compacts/current", params={"project": "alexandria-hermes"}
            )
            counts = anyio.run(_compact_persistence_counts, session, compact_id)
    finally:
        anyio.run(_close_service, database, session_context, session)

    assert create_response.status_code == 201
    assert delete_response.status_code == 204
    assert delete_response.content == b""
    assert get_response.status_code == 404
    assert list_response.status_code == 200
    assert list_response.json()["total"] == 0
    assert current_response.status_code == 404
    assert counts == {"compacts": 0, "source_refs": 0}


def test_memory_compact_api_exposes_current_archive_lifecycle(tmp_path: Path) -> None:
    """Memory Compact API should expose list/current/get/archive lifecycle."""
    database, session_context, session, service = anyio.run(
        _open_service, tmp_path / "compact-api.db"
    )
    try:
        with (
            override_library_provider("memory_compact_service", service),
            TestClient(app, raise_server_exceptions=False) as client,
        ):
            create_response = client.post("/memory/compacts", json=_payload())
            compact_id = create_response.json()["id"]
            current_response = client.get(
                "/memory/compacts/current", params={"project": "alexandria-hermes"}
            )
            get_response = client.get(f"/memory/compacts/{compact_id}")
            list_response = client.get(
                "/memory/compacts", params={"project": "alexandria-hermes"}
            )
            archive_response = client.post(f"/memory/compacts/{compact_id}/archive")
    finally:
        anyio.run(_close_service, database, session_context, session)

    assert create_response.status_code == 201
    assert create_response.json()["status"] == "CURRENT"
    assert create_response.json()["source_refs"][0]["source_id"] == "ctx-1"
    assert current_response.status_code == 200
    assert current_response.json()["id"] == compact_id
    assert get_response.status_code == 200
    assert get_response.json()["markdown_body"].startswith("## 2026-05-01")
    assert list_response.status_code == 200
    assert list_response.json()["total"] == 1
    assert archive_response.status_code == 200
    assert archive_response.json()["status"] == "ARCHIVED"


def test_memory_compact_api_filters_by_dates_when_requested(tmp_path: Path) -> None:
    """Memory Compact API should filter by coverage overlap."""
    database, session_context, session, service = anyio.run(
        _open_service, tmp_path / "compact-date-filters.db"
    )
    try:
        with (
            override_library_provider("memory_compact_service", service),
            TestClient(app, raise_server_exceptions=False) as client,
        ):
            may_response = client.post(
                "/memory/compacts",
                json=_payload(
                    "DRAFT",
                    covered_from="2026-05-01T00:00:00Z",
                    covered_to="2026-05-10T00:00:00Z",
                    source_id="ctx-may",
                ),
            )
            june_response = client.post(
                "/memory/compacts",
                json=_payload(
                    "DRAFT",
                    covered_from="2026-06-01T00:00:00Z",
                    covered_to="2026-06-10T00:00:00Z",
                    source_id="ctx-june",
                ),
            )
            coverage_response = client.get(
                "/memory/compacts",
                params={
                    "project": "alexandria-hermes",
                    "covered_after": "2026-05-05T00:00:00Z",
                    "covered_before": "2026-05-06T23:59:59Z",
                },
            )
            naive_response = client.get(
                "/memory/compacts",
                params={"covered_after": "2026-05-05T00:00:00"},
            )
    finally:
        anyio.run(_close_service, database, session_context, session)

    assert may_response.status_code == 201
    assert june_response.status_code == 201
    assert coverage_response.status_code == 200
    coverage_payload = coverage_response.json()
    assert coverage_payload["total"] == 1
    assert [item["id"] for item in coverage_payload["items"]] == [
        may_response.json()["id"]
    ]
    assert naive_response.status_code == 422


def test_memory_compact_api_rejects_non_iso_datetime_without_server_error(
    tmp_path: Path,
) -> None:
    """Memory Compact API should return validation errors for invalid datetimes."""
    database, session_context, session, service = anyio.run(
        _open_service, tmp_path / "compact-invalid-datetime.db"
    )
    try:
        with (
            override_library_provider("memory_compact_service", service),
            TestClient(app, raise_server_exceptions=False) as client,
        ):
            payload = _payload()
            payload["covered_from"] = 123
            response = client.post("/memory/compacts", json=payload)
    finally:
        anyio.run(_close_service, database, session_context, session)

    assert response.status_code == 422
