"""sqlite-vec loading and health helpers."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass

from app.memory.domain.event_enum.context_enums import RagHealthState


@dataclass(frozen=True, slots=True)
class SqliteVecStatus:
    """Health result for sqlite-vec extension loading."""

    state: RagHealthState
    version: str | None
    message: str


def probe_sqlite_vec() -> SqliteVecStatus:
    """Probe sqlite-vec in an isolated in-memory SQLite connection.

    Returns:
        Health status for sqlite-vec extension loading.
    """
    try:
        import sqlite_vec
    except Exception as exc:
        return SqliteVecStatus(
            state=RagHealthState.DEGRADED,
            version=None,
            message=f"sqlite-vec import failed: {exc}",
        )

    try:
        with sqlite3.connect(":memory:") as connection:
            connection.enable_load_extension(True)
            sqlite_vec.load(connection)
            version = str(connection.execute("select vec_version()").fetchone()[0])
            return SqliteVecStatus(
                state=RagHealthState.HEALTHY,
                version=version,
                message="sqlite-vec loaded",
            )
    except Exception as exc:
        return SqliteVecStatus(
            state=RagHealthState.DEGRADED,
            version=None,
            message=f"sqlite-vec load failed: {exc}",
        )
