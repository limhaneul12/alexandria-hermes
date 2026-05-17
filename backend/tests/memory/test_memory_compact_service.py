"""Memory Compact service behavior tests."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from pathlib import Path

import anyio
import pytest
from app.memory.application.memory_compact_service import MemoryCompactService
from app.memory.domain.event_enum.memory_compact_enums import (
    MemoryCompactStatus,
)
from app.memory.domain.repositories.memory_compact_repository import (
    MemoryCompactCreate,
    MemoryCompactSourceRefCreate,
)
from app.memory.infrastructure.repositories.memory_compact_repository import (
    SqlAlchemyMemoryCompactRepository,
)
from app.shared.exceptions import MemoryCompactValidationError
from app.shared.infrastructure.database import Database


@asynccontextmanager
async def _temporary_database(path: Path) -> AsyncIterator[Database]:
    database = Database(database_url=f"sqlite+aiosqlite:///{path}", create_schema=True)
    await database.initialize()
    try:
        yield database
    finally:
        await database.shutdown()


def _source_ref(source_id: str = "ctx-1") -> MemoryCompactSourceRefCreate:
    return MemoryCompactSourceRefCreate(
        source_type="CONTEXT",
        source_id=source_id,
        title="Context source",
        detail_path=f"/memory/contexts/{source_id}",
    )


def _create(status: MemoryCompactStatus) -> MemoryCompactCreate:
    return MemoryCompactCreate(
        project="alexandria-hermes",
        covered_from=datetime(2026, 5, 1, tzinfo=UTC),
        covered_to=datetime(2026, 5, 10, tzinfo=UTC),
        markdown_body="## 2026-05-01 to 2026-05-10\nDurable summary.",
        status=status,
        source_refs=[_source_ref()],
    )


def test_memory_compact_service_supersedes_previous_current_when_new_current_created(
    tmp_path: Path,
) -> None:
    """Project should have one CURRENT compact and archive/supersede history."""

    async def scenario() -> None:
        async with (
            _temporary_database(tmp_path / "compacts.db") as database,
            database.session() as session,
        ):
            service = MemoryCompactService(
                repository=SqlAlchemyMemoryCompactRepository(session=session)
            )
            first = await service.create(_create(MemoryCompactStatus.CURRENT))
            second_payload = _create(MemoryCompactStatus.CURRENT)
            second = await service.create(
                MemoryCompactCreate(
                    project=second_payload.project,
                    covered_from=datetime(2026, 5, 11, tzinfo=UTC),
                    covered_to=datetime(2026, 5, 15, tzinfo=UTC),
                    markdown_body="## 2026-05-11 to 2026-05-15\nNew durable summary.",
                    status=MemoryCompactStatus.CURRENT,
                    source_refs=[_source_ref("ctx-2")],
                )
            )
            await session.commit()
            current = await service.current(project="alexandria-hermes")
            previous = await service.get(first.id)
            listed, total = await service.list_compacts(project="alexandria-hermes")

        assert total == 2
        assert current.id == second.id
        assert previous.status is MemoryCompactStatus.SUPERSEDED
        assert [item.id for item in listed] == [second.id, first.id]

    anyio.run(scenario)


def test_current_memory_compact_requires_source_refs(tmp_path: Path) -> None:
    """Current compacts should not be accepted without source refs."""

    async def scenario() -> None:
        async with (
            _temporary_database(tmp_path / "source-refs.db") as database,
            database.session() as session,
        ):
            service = MemoryCompactService(
                repository=SqlAlchemyMemoryCompactRepository(session=session)
            )
            with pytest.raises(MemoryCompactValidationError, match="source refs"):
                await service.create(
                    MemoryCompactCreate(
                        project="alexandria-hermes",
                        covered_from=datetime(2026, 5, 1, tzinfo=UTC),
                        covered_to=datetime(2026, 5, 10, tzinfo=UTC),
                        markdown_body="## 2026-05-01 to 2026-05-10\nNo refs.",
                        status=MemoryCompactStatus.CURRENT,
                        source_refs=[],
                    )
                )

    anyio.run(scenario)
