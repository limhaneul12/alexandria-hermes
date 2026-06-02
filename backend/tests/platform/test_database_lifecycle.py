"""Database lifecycle contracts for migration-managed runtime schema."""

from __future__ import annotations

import sqlite3
from pathlib import Path

import anyio
from app.shared.infrastructure.database import SQLITE_BUSY_TIMEOUT_MS, Database
from sqlalchemy import text


def _table_names(database_path: Path) -> set[str]:
    connection = sqlite3.connect(database_path)
    try:
        rows = connection.execute(
            "SELECT name FROM sqlite_master WHERE type IN ('table', 'virtual table')"
        ).fetchall()
    finally:
        connection.close()
    return {str(row[0]) for row in rows}


def test_database_initialize_does_not_create_archive_schema_without_explicit_opt_in(
    tmp_path: Path,
) -> None:
    """Runtime database startup should not bypass Alembic by creating tables."""

    async def scenario() -> None:
        database_path = tmp_path / "runtime.db"
        database = Database(database_url=f"sqlite+aiosqlite:///{database_path}")
        await database.initialize()
        await database.shutdown()

        assert database_path.exists()
        assert "library_items" not in _table_names(database_path)
        assert "item_search_fts" not in _table_names(database_path)

    anyio.run(scenario)


def test_database_initialize_can_create_schema_for_isolated_repository_tests(
    tmp_path: Path,
) -> None:
    """Repository tests can still request throwaway backend schema creation."""

    async def scenario() -> None:
        database_path = tmp_path / "test.db"
        database = Database(
            database_url=f"sqlite+aiosqlite:///{database_path}",
            create_schema=True,
        )
        await database.initialize()
        await database.shutdown()

        table_names = _table_names(database_path)
        assert "contexts" in table_names
        assert "memory_compacts" not in table_names
        assert "memory_compact_source_refs" not in table_names
        assert "library_items" not in table_names
        assert "item_search_fts" not in table_names

    anyio.run(scenario)


def test_sqlite_connections_use_wal_and_extended_busy_timeout(
    tmp_path: Path,
) -> None:
    """SQLite runtime connections should tolerate local read/write contention."""

    async def scenario() -> None:
        database_path = tmp_path / "contention.db"
        database = Database(database_url=f"sqlite+aiosqlite:///{database_path}")
        await database.initialize()
        try:
            async with database.session_factory()() as session:
                timeout = await session.scalar(text("PRAGMA busy_timeout"))
                journal_mode = await session.scalar(text("PRAGMA journal_mode"))
                synchronous = await session.scalar(text("PRAGMA synchronous"))

            assert timeout == SQLITE_BUSY_TIMEOUT_MS
            assert journal_mode == "wal"
            assert synchronous == 1
        finally:
            await database.shutdown()

    anyio.run(scenario)
