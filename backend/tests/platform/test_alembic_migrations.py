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
        memory_compact_columns = {
            row[1]: row[2]
            for row in connection.execute(
                "PRAGMA table_info(memory_compacts)"
            ).fetchall()
        }
        memory_compact_indexes = {
            row[1]: row[2]
            for row in connection.execute(
                "PRAGMA index_list(memory_compacts)"
            ).fetchall()
        }
        skill_acquisition_job_columns = {
            row[1]: row[2]
            for row in connection.execute(
                "PRAGMA table_info(skill_acquisition_jobs)"
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
        contexts_definition = connection.execute(
            "SELECT sql FROM sqlite_master WHERE name = 'contexts'"
        ).fetchone()[0]

    assert category_columns["id"] == "VARCHAR(36)"
    assert category_columns["parent_id"] == "VARCHAR(36)"
    assert item_columns["id"] == "VARCHAR(36)"
    assert item_columns["category_id"] == "VARCHAR(36)"
    assert context_columns["id"] == "VARCHAR(36)"
    assert context_columns["kind"] == "VARCHAR(32)"
    assert chunk_columns["context_id"] == "VARCHAR(36)"
    assert memory_compact_columns["id"] == "VARCHAR(36)"
    assert memory_compact_columns["status"] == "VARCHAR(24)"
    assert skill_acquisition_job_columns["id"] == "VARCHAR(36)"
    assert skill_acquisition_job_columns["status"] == "VARCHAR(32)"
    assert skill_acquisition_job_columns["evidence_urls"] == "JSON"
    assert memory_compact_indexes["uq_memory_compacts_current_project"] == 1
    assert memory_compact_indexes["uq_memory_compacts_current_default_project"] == 1
    assert "item_id UNINDEXED" in fts_definition
    assert "chunk_id UNINDEXED" in context_fts_definition
    assert "'HARNESS'" in contexts_definition
    assert speculative_tables == set()


def test_alembic_upgrade_removes_legacy_minio_providers_when_present(
    tmp_path: Path,
) -> None:
    """Alembic should remove legacy MINIO providers and their stored secrets."""

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
        remaining_minio_secrets = connection.execute(
            """
            SELECT COUNT(*)
            FROM librarian_provider_secrets
            WHERE provider_id IN ('legacy-smoke-provider', 'real-minio-provider')
            """
        ).fetchone()[0]

    assert remaining_providers == []
    assert remaining_minio_secrets == 0


def test_alembic_upgrade_removes_legacy_workflow_library_items(
    tmp_path: Path,
) -> None:
    """Alembic should delete legacy WORKFLOW rows and reject new workflow items."""

    database_path = tmp_path / "workflow-item-type.db"
    previous_revision = "202605172010_add_context_access_events"
    result = _run_alembic(database_path, previous_revision)
    assert result.returncode == 0, result.stderr

    with sqlite3.connect(database_path) as connection:
        connection.executescript(
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
                'workflow-item',
                'WORKFLOW',
                'Legacy workflow item',
                NULL,
                'Legacy workflow content',
                NULL,
                '[]',
                'ACTIVE',
                'USER_CREATED',
                'USER',
                'Hermes',
                '2026-05-18 00:00:00',
                '2026-05-18 00:00:00',
                '{}',
                0
            );
            INSERT INTO usage_histories (
                id,
                item_id,
                item_type,
                agent_name,
                librarian_provider,
                query,
                selection_source,
                used_at,
                success,
                feedback
            )
            VALUES (
                'workflow-usage',
                'workflow-item',
                'WORKFLOW',
                'Hermes',
                NULL,
                NULL,
                'MANUAL_BROWSE',
                '2026-05-18 00:00:00',
                1,
                NULL
            );
            """
        )

    result = _run_alembic(database_path, "head")
    assert result.returncode == 0, result.stderr

    with sqlite3.connect(database_path) as connection:
        workflow_count = connection.execute(
            "SELECT COUNT(*) FROM library_items WHERE item_type = 'WORKFLOW'"
        ).fetchone()[0]
        usage_count = connection.execute(
            "SELECT COUNT(*) FROM usage_histories WHERE id = 'workflow-usage'"
        ).fetchone()[0]

        try:
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
                    'new-workflow-item',
                    'WORKFLOW',
                    'Rejected workflow item',
                    NULL,
                    'Should fail',
                    NULL,
                    '[]',
                    'ACTIVE',
                    'USER_CREATED',
                    'USER',
                    'Hermes',
                    '2026-05-18 00:00:00',
                    '2026-05-18 00:00:00',
                    '{}',
                    0
                )
                """
            )
        except sqlite3.IntegrityError:
            workflow_rejected = True
        else:
            workflow_rejected = False

    assert workflow_count == 0
    assert usage_count == 0
    assert workflow_rejected is True


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
