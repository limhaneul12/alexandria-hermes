"""Alembic migration runner used by local setup commands."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from alembic import command
from alembic.config import Config


@dataclass(frozen=True, slots=True, kw_only=True)
class MigrationRunResult:
    """Result for a setup-triggered Alembic upgrade."""

    status: str
    revision: str


def run_alembic_upgrade(
    *, database_url: str, revision: str = "head"
) -> MigrationRunResult:
    """Run Alembic migrations against the generated local database URL.

    Args:
        database_url: SQLAlchemy database URL to expose to Alembic env.py.
        revision: Alembic target revision.

    Returns:
        Migration run summary.
    """
    config = _alembic_config(database_url)
    command.upgrade(config, revision)
    return MigrationRunResult(status="upgraded", revision=revision)


def _alembic_config(database_url: str) -> Config:
    backend_root = Path(__file__).resolve().parents[3]
    config = Config(str(backend_root / "alembic.ini"))
    config.set_main_option("sqlalchemy.url", database_url)
    return config
