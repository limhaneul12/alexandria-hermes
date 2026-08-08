"""Alembic runtime transaction contracts."""

from __future__ import annotations

from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[2]


def test_async_migrations_commit_the_postgres_version_table_and_schema() -> None:
    """PostgreSQL bootstrap DDL and migrations must share one committed transaction."""
    source = (BACKEND_ROOT / "migrations" / "env.py").read_text(encoding="utf-8")

    assert "async with connectable.begin() as connection:" in source
    assert "async with connectable.connect() as connection:" not in source
    assert "version_num VARCHAR(255) NOT NULL PRIMARY KEY" in source


def test_alembic_uses_the_canonical_async_database_configuration() -> None:
    """Generic DATABASE_URL schemes must be normalized before engine creation."""
    source = (BACKEND_ROOT / "migrations" / "env.py").read_text(encoding="utf-8")

    assert "from app.platform.config.database_config import DatabaseConfig" in source
    assert 'config.set_main_option("sqlalchemy.url", DatabaseConfig().url)' in source
    assert 'os.environ.get("DATABASE_URL")' not in source
