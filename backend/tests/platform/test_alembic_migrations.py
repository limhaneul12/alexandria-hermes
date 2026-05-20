"""Alembic migration contract tests."""

from __future__ import annotations

import base64
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


def test_alembic_upgrade_rejects_removed_legacy_library_item_types(
    tmp_path: Path,
) -> None:
    """Baseline schema should reject legacy library item families."""

    database_path = tmp_path / "removed-item-types.db"
    result = _run_alembic(database_path, "head")
    assert result.returncode == 0, result.stderr

    rejected_item_types: list[str] = []
    with sqlite3.connect(database_path) as connection:
        for item_type in ("WORKFLOW", "KNOWLEDGE"):
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
                        ?,
                        ?,
                        'Rejected legacy item',
                        NULL,
                        'Should fail',
                        NULL,
                        '[]',
                        'ACTIVE',
                        'USER_CREATED',
                        'USER',
                        'Hermes',
                        '2026-05-19 00:00:00',
                        '2026-05-19 00:00:00',
                        '{}',
                        0
                    )
                    """,
                    (f"legacy-{item_type.lower()}", item_type),
                )
            except sqlite3.IntegrityError:
                rejected_item_types.append(item_type)

    assert rejected_item_types == ["WORKFLOW", "KNOWLEDGE"]


def test_alembic_upgrade_marks_legacy_sqlite_datetimes_as_utc(
    tmp_path: Path,
) -> None:
    """Alembic should mark existing naive SQLite timestamp rows as UTC."""

    database_path = tmp_path / "legacy-naive-datetimes.db"
    previous_revision = "202605192115_remove_knowledge_library_item_type"
    result = _run_alembic(database_path, previous_revision)
    assert result.returncode == 0, result.stderr

    with sqlite3.connect(database_path) as connection:
        connection.executescript(
            """
            INSERT INTO agent_profiles (
                id,
                name,
                provider,
                capabilities,
                created_at,
                updated_at
            )
            VALUES (
                'agent-with-naive-datetime',
                'Agent With Naive Datetime',
                'OPENAI',
                '[]',
                '2026-05-16 04:32:36.331519',
                '2026-05-16 04:32:52+09:00'
            );
            INSERT INTO skill_acquisition_jobs (
                id,
                prompt,
                agent_name,
                status,
                evidence_urls,
                created_at,
                updated_at,
                completed_at
            )
            VALUES (
                'job-with-naive-datetime',
                'Acquire skill',
                'Hermes',
                'COMPLETED',
                '[]',
                '2026-05-18 17:20:00',
                '2026-05-18 17:20:01Z',
                '2026-05-18 17:21:00'
            );
            """
        )

    result = _run_alembic(database_path, "head")
    assert result.returncode == 0, result.stderr

    with sqlite3.connect(database_path) as connection:
        agent_created_at, agent_updated_at = connection.execute(
            """
            SELECT created_at, updated_at
            FROM agent_profiles
            WHERE id = 'agent-with-naive-datetime'
            """
        ).fetchone()
        job_created_at, job_updated_at, job_completed_at = connection.execute(
            """
            SELECT created_at, updated_at, completed_at
            FROM skill_acquisition_jobs
            WHERE id = 'job-with-naive-datetime'
            """
        ).fetchone()

    assert {
        "agent_created_at": agent_created_at,
        "agent_updated_at": agent_updated_at,
        "job_created_at": job_created_at,
        "job_updated_at": job_updated_at,
        "job_completed_at": job_completed_at,
    } == {
        "agent_created_at": "2026-05-16 04:32:36.331519+00:00",
        "agent_updated_at": "2026-05-16 04:32:52+09:00",
        "job_created_at": "2026-05-18 17:20:00+00:00",
        "job_updated_at": "2026-05-18 17:20:01Z",
        "job_completed_at": "2026-05-18 17:21:00+00:00",
    }


def test_alembic_upgrade_rejects_legacy_plaintext_provider_secrets(
    tmp_path: Path,
) -> None:
    """Alembic should fail closed when old plaintext provider secrets remain."""

    database_path = tmp_path / "legacy-provider-secret.db"
    previous_revision = "202605201020_normalize_legacy_sqlite_datetimes"
    result = _run_alembic(database_path, previous_revision)
    assert result.returncode == 0, result.stderr

    with sqlite3.connect(database_path) as connection:
        connection.executescript(
            """
            INSERT INTO librarian_providers (
                id,
                name,
                provider_type,
                auth_type,
                enabled,
                config,
                created_at,
                updated_at
            )
            VALUES (
                'provider-with-legacy-secret',
                'Legacy secret provider',
                'OPENAI',
                'API_KEY',
                1,
                '{}',
                '2026-05-20 00:00:00+00:00',
                '2026-05-20 00:00:00+00:00'
            );
            INSERT INTO librarian_provider_secrets (
                id,
                provider_id,
                key_name,
                value
            )
            VALUES (
                'legacy-secret-row',
                'provider-with-legacy-secret',
                'api_key',
                'plain-secret'
            );
            """
        )

    result = _run_alembic(database_path, "head")

    assert result.returncode != 0
    assert "Legacy plaintext or old-version provider secrets" in result.stderr


def test_alembic_upgrade_rejects_old_version_opaque_provider_secrets(
    tmp_path: Path,
) -> None:
    """Alembic should fail closed when opaque provider secrets use an old version."""

    database_path = tmp_path / "old-version-provider-secret.db"
    previous_revision = "202605201020_normalize_legacy_sqlite_datetimes"
    result = _run_alembic(database_path, previous_revision)
    assert result.returncode == 0, result.stderr
    old_version_payload = base64.urlsafe_b64encode(bytes([2]) + b"x" * 28).decode(
        "ascii"
    )

    with sqlite3.connect(database_path) as connection:
        connection.executescript(
            f"""
            INSERT INTO librarian_providers (
                id,
                name,
                provider_type,
                auth_type,
                enabled,
                config,
                created_at,
                updated_at
            )
            VALUES (
                'provider-with-old-secret',
                'Old secret provider',
                'OPENAI',
                'API_KEY',
                1,
                '{{}}',
                '2026-05-20 00:00:00+00:00',
                '2026-05-20 00:00:00+00:00'
            );
            INSERT INTO librarian_provider_secrets (
                id,
                provider_id,
                key_name,
                value
            )
            VALUES (
                'old-version-secret-row',
                'provider-with-old-secret',
                'api_key',
                '{old_version_payload}'
            );
            """
        )

    result = _run_alembic(database_path, "head")

    assert result.returncode != 0
    assert "Legacy plaintext or old-version provider secrets" in result.stderr


def test_alembic_upgrade_deletes_legacy_plaintext_oauth_provider_secrets(
    tmp_path: Path,
) -> None:
    """Alembic should clear invalid OAuth material instead of blocking upgrade."""

    database_path = tmp_path / "legacy-oauth-secret.db"
    previous_revision = "202605201020_normalize_legacy_sqlite_datetimes"
    result = _run_alembic(database_path, previous_revision)
    assert result.returncode == 0, result.stderr

    with sqlite3.connect(database_path) as connection:
        connection.executescript(
            """
            INSERT INTO librarian_providers (
                id,
                name,
                provider_type,
                auth_type,
                enabled,
                config,
                created_at,
                updated_at
            )
            VALUES (
                'provider-with-legacy-oauth-secret',
                'Legacy OAuth provider',
                'OPENAI_CODEX',
                'OAUTH',
                1,
                '{}',
                '2026-05-20 00:00:00+00:00',
                '2026-05-20 00:00:00+00:00'
            );
            INSERT INTO librarian_provider_secrets (
                id,
                provider_id,
                key_name,
                value
            )
            VALUES (
                'legacy-oauth-secret-row',
                'provider-with-legacy-oauth-secret',
                'oauth_access_token',
                'plain-oauth-token'
            );
            """
        )

    result = _run_alembic(database_path, "head")

    assert result.returncode == 0, result.stderr
    with sqlite3.connect(database_path) as connection:
        remaining = connection.execute(
            """
            SELECT COUNT(*) FROM librarian_provider_secrets
            WHERE provider_id = 'provider-with-legacy-oauth-secret'
            """
        ).fetchone()[0]
    assert remaining == 0


def test_alembic_upgrade_deletes_old_version_oauth_provider_secrets(
    tmp_path: Path,
) -> None:
    """Alembic should clear obsolete opaque OAuth material during upgrade."""

    database_path = tmp_path / "old-version-oauth-secret.db"
    previous_revision = "202605201020_normalize_legacy_sqlite_datetimes"
    result = _run_alembic(database_path, previous_revision)
    assert result.returncode == 0, result.stderr
    old_version_payload = base64.urlsafe_b64encode(bytes([2]) + b"x" * 28).decode(
        "ascii"
    )

    with sqlite3.connect(database_path) as connection:
        connection.executescript(
            f"""
            INSERT INTO librarian_providers (
                id,
                name,
                provider_type,
                auth_type,
                enabled,
                config,
                created_at,
                updated_at
            )
            VALUES (
                'provider-with-old-oauth-secret',
                'Old OAuth provider',
                'OPENAI_CODEX',
                'OAUTH',
                1,
                '{{}}',
                '2026-05-20 00:00:00+00:00',
                '2026-05-20 00:00:00+00:00'
            );
            INSERT INTO librarian_provider_secrets (
                id,
                provider_id,
                key_name,
                value
            )
            VALUES (
                'old-oauth-secret-row',
                'provider-with-old-oauth-secret',
                'oauth_refresh_token',
                '{old_version_payload}'
            );
            """
        )

    result = _run_alembic(database_path, "head")

    assert result.returncode == 0, result.stderr
    with sqlite3.connect(database_path) as connection:
        remaining = connection.execute(
            """
            SELECT COUNT(*) FROM librarian_provider_secrets
            WHERE provider_id = 'provider-with-old-oauth-secret'
            """
        ).fetchone()[0]
    assert remaining == 0


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
