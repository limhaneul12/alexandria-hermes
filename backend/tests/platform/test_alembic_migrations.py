"""Alembic migration contract tests."""

from __future__ import annotations

import os
import sqlite3
import subprocess
from pathlib import Path


def _run_alembic(
    database_path: Path, revision: str
) -> subprocess.CompletedProcess[str]:
    env = os.environ | {"DATABASE_URL": f"sqlite+aiosqlite:///{database_path}"}
    return subprocess.run(
        ["uv", "run", "alembic", "upgrade", revision],
        cwd=Path(__file__).resolve().parents[2],
        env=env,
        check=False,
        capture_output=True,
        text=True,
    )


def test_alembic_upgrade_creates_uuid_backed_archive_schema(tmp_path: Path) -> None:
    """Alembic should be able to build the backend-owned SQLite schema from scratch."""

    database_path = tmp_path / "alembic.db"
    result = _run_alembic(database_path, "head")

    assert result.returncode == 0, result.stderr
    with sqlite3.connect(database_path) as connection:
        category_columns = {
            row[1]: row[2]
            for row in connection.execute("PRAGMA table_info(categories)").fetchall()
        }
        item_columns = {
            row[1]: row[2]
            for row in connection.execute("PRAGMA table_info(library_items)").fetchall()
        }
        context_columns = {
            row[1]: row[2]
            for row in connection.execute("PRAGMA table_info(contexts)").fetchall()
        }
        chunk_columns = {
            row[1]: row[2]
            for row in connection.execute(
                "PRAGMA table_info(context_chunks)"
            ).fetchall()
        }
        fts_definition = connection.execute(
            "SELECT sql FROM sqlite_master WHERE name = 'item_search_fts'"
        ).fetchone()[0]
        context_fts_definition = connection.execute(
            "SELECT sql FROM sqlite_master WHERE name = 'context_chunk_fts'"
        ).fetchone()[0]
        speculative_tables = {
            row[0]
            for row in connection.execute(
                """
                SELECT name FROM sqlite_master
                WHERE name IN (
                    'context_links',
                    'context_embeddings',
                    'context_chunk_vec'
                )
                """
            ).fetchall()
        }

    assert category_columns["id"] == "VARCHAR(36)"
    assert category_columns["parent_id"] == "VARCHAR(36)"
    assert item_columns["id"] == "VARCHAR(36)"
    assert item_columns["category_id"] == "VARCHAR(36)"
    assert context_columns["id"] == "VARCHAR(36)"
    assert context_columns["kind"] == "VARCHAR(32)"
    assert chunk_columns["context_id"] == "VARCHAR(36)"
    assert "item_id UNINDEXED" in fts_definition
    assert "chunk_id UNINDEXED" in context_fts_definition
    assert speculative_tables == set()


def test_alembic_upgrade_removes_legacy_default_minio_provider_when_present(
    tmp_path: Path,
) -> None:
    """Alembic should clean old smoke MINIO credentials without touching real providers."""

    database_path = tmp_path / "legacy-minio.db"
    previous_revision = "202605141904_add_context_vault"
    result = _run_alembic(database_path, previous_revision)
    assert result.returncode == 0, result.stderr

    with sqlite3.connect(database_path) as connection:
        connection.executescript(
            """
            INSERT INTO librarian_providers (
                id, name, provider_type, auth_type, enabled, config, created_at, updated_at
            )
            VALUES (
                'legacy-smoke-provider',
                'default-minio',
                'MINIO',
                'API_KEY',
                0,
                '{"endpoint":"http://localhost:9000","bucket":"alexandria-smoke"}',
                '2026-05-15 00:00:00',
                '2026-05-15 00:00:00'
            );
            INSERT INTO librarian_provider_secrets (id, provider_id, key_name, value)
            VALUES ('legacy-smoke-secret', 'legacy-smoke-provider', 'api_key', 'redacted');
            INSERT INTO librarian_providers (
                id, name, provider_type, auth_type, enabled, config, created_at, updated_at
            )
            VALUES (
                'real-minio-provider',
                'team-minio',
                'MINIO',
                'API_KEY',
                0,
                '{"endpoint":"http://localhost:9000","bucket":"team-archive"}',
                '2026-05-15 00:00:00',
                '2026-05-15 00:00:00'
            );
            """
        )

    result = _run_alembic(database_path, "head")
    assert result.returncode == 0, result.stderr

    with sqlite3.connect(database_path) as connection:
        remaining_providers = connection.execute(
            "SELECT id, name FROM librarian_providers ORDER BY id"
        ).fetchall()
        remaining_legacy_secrets = connection.execute(
            """
            SELECT COUNT(*)
            FROM librarian_provider_secrets
            WHERE provider_id = 'legacy-smoke-provider'
            """
        ).fetchone()[0]

    assert remaining_providers == [("real-minio-provider", "team-minio")]
    assert remaining_legacy_secrets == 0


def test_alembic_upgrade_allows_prompt_library_items(tmp_path: Path) -> None:
    """Alembic should allow PROMPT rows because prompt records share library_items."""

    database_path = tmp_path / "prompt-item-type.db"
    result = _run_alembic(database_path, "head")
    assert result.returncode == 0, result.stderr

    with sqlite3.connect(database_path) as connection:
        connection.execute(
            """
            INSERT INTO library_items (
                id,
                item_type,
                title,
                summary,
                content,
                category_id,
                tags,
                status,
                source_type,
                created_by_type,
                created_by_name,
                created_at,
                updated_at,
                details,
                is_archived
            )
            VALUES (
                'prompt-item',
                'PROMPT',
                'Prompt item',
                NULL,
                'Prompt content',
                NULL,
                '[]',
                'ACTIVE',
                'AGENT_SUBMITTED',
                'AGENT',
                'Hermes',
                '2026-05-15 00:00:00',
                '2026-05-15 00:00:00',
                '{}',
                0
            )
            """
        )
        inserted_type = connection.execute(
            "SELECT item_type FROM library_items WHERE id = 'prompt-item'"
        ).fetchone()[0]

    assert inserted_type == "PROMPT"
