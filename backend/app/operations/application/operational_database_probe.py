"""Database reachability, integrity, and schema-version probe."""

from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.operations.domain.entities.operational_readiness import (
    OperationalDatabaseSnapshot,
)
from app.shared.infrastructure.database import Database
from app.shared.infrastructure.sqlite_database_policy import is_sqlite_corruption_error


class OperationalDatabaseProbe:
    """Build the database portion of an operational readiness snapshot."""

    def __init__(self, database: Database) -> None:
        """Initialize the database probe.

        Args:
            database: Shared database coordinator.
        """
        self._database = database

    async def snapshot(self) -> OperationalDatabaseSnapshot:
        try:
            async with self._database.session_factory()() as session:
                quick_check = await session.scalar(text("PRAGMA quick_check"))
                schema_version = await _schema_version(session)
        except SQLAlchemyError as exc:
            corruption = is_sqlite_corruption_error(exc)
            return OperationalDatabaseSnapshot(
                reachable=False,
                integrity="CORRUPTION_DETECTED" if corruption else "UNAVAILABLE",
                schema_version=None,
                corruption_detected=corruption,
            )
        integrity = "HEALTHY" if quick_check == "ok" else "FAILED"
        return OperationalDatabaseSnapshot(
            reachable=True,
            integrity=integrity,
            schema_version=schema_version,
            corruption_detected=False,
        )


async def _schema_version(session: AsyncSession) -> str | None:
    table_exists = await session.scalar(
        text(
            "SELECT name FROM sqlite_master "
            "WHERE type = 'table' AND name = 'alembic_version'"
        )
    )
    if table_exists is None:
        return "unknown"
    version = await session.scalar(text("SELECT version_num FROM alembic_version"))
    return None if version is None else str(version)
