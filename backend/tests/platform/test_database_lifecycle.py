"""Database lifecycle contracts for migration-managed runtime schema."""

from __future__ import annotations

import sqlite3
from pathlib import Path

import anyio
import app.connections.infrastructure.models.librarian_provider_models as _librarian_provider_models
import app.librarian.infrastructure.models.agent_models as _agent_models
import app.librarian.infrastructure.models.skill_acquisition_job_models as _skill_acquisition_job_models
import app.memory.infrastructure.models.context_models as _context_models
import app.obsidian.infrastructure.models.obsidian_index_models as _obsidian_index_models
import app.shared.infrastructure.sqlite_database_policy as sqlite_database_policy
import pytest
from app.shared.infrastructure.database import Database
from app.shared.infrastructure.sqlite_database_policy import (
    SQLITE_BUSY_TIMEOUT_MS,
    install_sqlite_connection_pragmas,
    is_sqlite_corruption_error,
)
from sqlalchemy import text
from sqlalchemy.exc import DatabaseError

_ORM_MODELS_LOADED = (
    _agent_models,
    _context_models,
    _librarian_provider_models,
    _obsidian_index_models,
    _skill_acquisition_job_models,
)


class _RecordingCursor:
    def __init__(self) -> None:
        self.statements: list[str] = []

    def execute(self, statement: str) -> None:
        self.statements.append(statement)

    def close(self) -> None:
        pass


class _RecordingConnection:
    def __init__(self) -> None:
        self.cursor_instance = _RecordingCursor()

    def cursor(self) -> _RecordingCursor:
        return self.cursor_instance


class _FakeAsyncEngine:
    def __init__(self) -> None:
        self.sync_engine = object()


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


def test_sqlite_wal_mode_is_configured_once_per_pool(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Journal mode must not be mutated for every pooled SQLite connection."""
    callbacks: dict[str, object] = {}

    def fake_listens_for(_target: object, event_name: str):
        def register(callback):
            callbacks[event_name] = callback
            return callback

        return register

    monkeypatch.setattr(
        sqlite_database_policy.event,
        "listens_for",
        fake_listens_for,
    )
    install_sqlite_connection_pragmas(_FakeAsyncEngine())  # type: ignore[arg-type]

    first_connection = _RecordingConnection()
    pooled_connection = _RecordingConnection()
    callbacks["first_connect"](first_connection, object())  # type: ignore[operator]
    callbacks["connect"](pooled_connection, object())  # type: ignore[operator]

    assert "PRAGMA journal_mode=WAL" in first_connection.cursor_instance.statements
    assert "PRAGMA journal_mode=WAL" not in pooled_connection.cursor_instance.statements
    assert pooled_connection.cursor_instance.statements == [
        f"PRAGMA busy_timeout={SQLITE_BUSY_TIMEOUT_MS}",
        "PRAGMA synchronous=NORMAL",
    ]


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


def test_new_sqlite_connection_does_not_reapply_wal_during_active_write(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Opening a pooled reader must not mutate journal mode under write contention."""
    monkeypatch.setattr(sqlite_database_policy, "SQLITE_BUSY_TIMEOUT_MS", 50)

    async def scenario() -> int:
        database_path = tmp_path / "active-write.db"
        database = Database(database_url=f"sqlite+aiosqlite:///{database_path}")
        await database.initialize()
        writer = database.session_factory()()
        try:
            async with database.engine.begin() as connection:
                await connection.execute(
                    text("CREATE TABLE contention_probe (value INTEGER NOT NULL)")
                )
            await writer.execute(
                text("INSERT INTO contention_probe (value) VALUES (1)")
            )

            async with database.session_factory()() as reader:
                scalar = await reader.scalar(text("SELECT 1"))
                return int(scalar or 0)
        finally:
            await writer.rollback()
            await writer.close()
            await database.shutdown()

    assert anyio.run(scenario) == 1


def test_database_recovers_from_sqlite_file_corruption_errors(
    tmp_path: Path,
) -> None:
    """SQLite file failures should drop stale pooled connections for later requests."""

    async def scenario() -> tuple[bool, int]:
        database_path = tmp_path / "recovered.db"
        database = Database(database_url=f"sqlite+aiosqlite:///{database_path}")
        await database.initialize()
        try:
            corruption_error = DatabaseError(
                "SELECT 1",
                {},
                sqlite3.DatabaseError("file is not a database"),
            )

            recovered = await database.recover_from_error(corruption_error)

            async with database.session_factory()() as session:
                scalar = await session.scalar(text("SELECT 1"))

            return recovered, int(scalar or 0)
        finally:
            await database.shutdown()

    recovered, scalar = anyio.run(scenario)

    assert recovered is True
    assert scalar == 1


def test_sqlite_corruption_detection_ignores_unrelated_database_errors() -> None:
    """Only file-level SQLite failures should trigger pool recovery."""
    integrity_error = DatabaseError(
        "INSERT INTO messages VALUES (?)",
        {},
        sqlite3.IntegrityError("UNIQUE constraint failed: messages.id"),
    )

    assert is_sqlite_corruption_error(integrity_error) is False
