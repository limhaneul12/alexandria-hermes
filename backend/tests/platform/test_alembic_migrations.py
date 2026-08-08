"""PostgreSQL Alembic head and schema contracts."""

from __future__ import annotations

import os

import anyio
from alembic.config import Config
from alembic.script import ScriptDirectory
from app.shared.infrastructure.database import Database
from sqlalchemy import text


def _expected_head() -> str:
    config = Config("alembic.ini")
    config.set_main_option("script_location", "migrations")
    head = ScriptDirectory.from_config(config).get_current_head()
    assert head is not None
    return head


def test_alembic_database_is_at_single_postgresql_head() -> None:
    """The migrated test database should match the repository's single Alembic head."""

    async def scenario() -> str | None:
        database = Database(database_url=os.environ["DATABASE_URL"])
        try:
            async with database.session_factory()() as session:
                return await session.scalar(
                    text("SELECT version_num FROM alembic_version")
                )
        finally:
            await database.shutdown()

    assert anyio.run(scenario) == _expected_head()


def test_alembic_head_has_postgresql_search_storage() -> None:
    """PostgreSQL head should include pgvector and canonical search tables."""

    async def scenario() -> tuple[bool, tuple[str, ...]]:
        database = Database(database_url=os.environ["DATABASE_URL"])
        try:
            async with database.session_factory()() as session:
                vector_present = bool(
                    await session.scalar(
                        text(
                            "SELECT EXISTS (SELECT 1 FROM pg_extension "
                            "WHERE extname = 'vector')"
                        )
                    )
                )
                rows = await session.execute(
                    text(
                        "SELECT tablename FROM pg_tables WHERE schemaname = 'public' "
                        "AND tablename IN ('contexts', 'context_chunks', "
                        "'obsidian_files', 'obsidian_chunks')"
                    )
                )
                return vector_present, tuple(sorted(str(row[0]) for row in rows))
        finally:
            await database.shutdown()

    assert anyio.run(scenario) == (
        True,
        ("context_chunks", "contexts", "obsidian_chunks", "obsidian_files"),
    )


def test_alembic_head_keeps_oauth_and_reconciliation_tables() -> None:
    """Current head should retain durable OAuth and reconciliation state."""

    async def scenario() -> tuple[str, ...]:
        database = Database(database_url=os.environ["DATABASE_URL"])
        try:
            async with database.session_factory()() as session:
                rows = await session.execute(
                    text(
                        "SELECT tablename FROM pg_tables WHERE schemaname = 'public' "
                        "AND (tablename LIKE 'mcp_oauth_%' "
                        "OR tablename LIKE 'memory_reconciliation_%')"
                    )
                )
                return tuple(sorted(str(row[0]) for row in rows))
        finally:
            await database.shutdown()

    tables = anyio.run(scenario)
    assert any(name.startswith("mcp_oauth_") for name in tables)
    assert any(name.startswith("memory_reconciliation_") for name in tables)


def test_alembic_head_does_not_restore_retired_library_crud_tables() -> None:
    """Retired SQLite-era library CRUD tables must remain absent at PostgreSQL head."""

    async def scenario() -> tuple[str, ...]:
        database = Database(database_url=os.environ["DATABASE_URL"])
        try:
            async with database.session_factory()() as session:
                rows = await session.execute(
                    text(
                        "SELECT tablename FROM pg_tables WHERE schemaname = 'public' "
                        "AND tablename IN ('library_items', 'prompt_library_items', "
                        "'memory_compact_artifacts')"
                    )
                )
                return tuple(str(row[0]) for row in rows)
        finally:
            await database.shutdown()

    assert anyio.run(scenario) == ()
