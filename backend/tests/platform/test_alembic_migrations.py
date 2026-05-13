"""Alembic migration contract tests."""

from __future__ import annotations

import os
import sqlite3
import subprocess
from pathlib import Path


def test_alembic_upgrade_creates_uuid_backed_archive_schema(tmp_path: Path) -> None:
    """Alembic should be able to build the backend-owned SQLite schema from scratch."""

    database_path = tmp_path / "alembic.db"
    env = os.environ | {"DATABASE_URL": f"sqlite+aiosqlite:///{database_path}"}

    result = subprocess.run(
        ["uv", "run", "alembic", "upgrade", "head"],
        cwd=Path(__file__).resolve().parents[2],
        env=env,
        check=False,
        capture_output=True,
        text=True,
    )

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
        fts_definition = connection.execute(
            "SELECT sql FROM sqlite_master WHERE name = 'item_search_fts'"
        ).fetchone()[0]

    assert category_columns["id"] == "VARCHAR(36)"
    assert category_columns["parent_id"] == "VARCHAR(36)"
    assert item_columns["id"] == "VARCHAR(36)"
    assert item_columns["category_id"] == "VARCHAR(36)"
    assert "item_id UNINDEXED" in fts_definition
