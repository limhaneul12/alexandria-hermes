"""Memory Compact router contract tests."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import anyio
from app.main import app
from app.memory.application.memory_compact_service import MemoryCompactService
from app.memory.infrastructure.repositories.memory_compact_repository import (
    SqlAlchemyMemoryCompactRepository,
)
from app.shared.infrastructure.database import Database
from fastapi.testclient import TestClient
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


def _payload(status: str = "CURRENT") -> dict[str, object]:
    return {
        "project": "alexandria-hermes",
        "covered_from": "2026-05-01T00:00:00Z",
        "covered_to": "2026-05-10T00:00:00Z",
        "markdown_body": "## 2026-05-01 to 2026-05-10\nDurable Memory Compact.",
        "status": status,
        "source_refs": [
            {
                "source_type": "CONTEXT",
                "source_id": "ctx-1",
                "title": "Context source",
                "detail_path": "/memory/contexts/ctx-1",
            }
        ],
    }


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
