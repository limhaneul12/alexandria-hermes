"""SQLite URL, connection, and corruption policies for database coordination."""

from __future__ import annotations

from pathlib import Path
from urllib.parse import urlparse

from sqlalchemy import event
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import AsyncEngine

SQLITE_BUSY_TIMEOUT_MS = 30_000
SQLITE_CORRUPTION_ERROR_MARKERS = (
    "database disk image is malformed",
    "file is not a database",
)


def sqlite_path_from_url(database_url: str) -> str | None:
    """Return a local filesystem path for a file-backed SQLite URL.

    Args:
        database_url: Async SQLAlchemy database URL.

    Returns:
        SQLite file path for file-backed SQLite URLs, otherwise ``None``.
    """
    parsed = urlparse(database_url)
    if parsed.scheme not in {"sqlite", "sqlite+aiosqlite"}:
        return None
    if parsed.path in {"", "/:memory:"}:
        return None
    if parsed.path.startswith("//"):
        return parsed.path[1:]
    return parsed.path.lstrip("/")


def ensure_sqlite_parent(sqlite_path: str | None) -> None:
    """Create the parent directory for a file-backed SQLite database.

    Args:
        sqlite_path: Local SQLite file path when configured.
    """
    if sqlite_path is not None:
        Path(sqlite_path).parent.mkdir(parents=True, exist_ok=True)


def install_sqlite_connection_pragmas(engine: AsyncEngine) -> None:
    """Apply pool and connection settings that prevent transient lock failures.

    Args:
        engine: Async SQLAlchemy engine backed by SQLite.
    """

    @event.listens_for(engine.sync_engine, "first_connect")
    def set_sqlite_pool_pragmas(dbapi_connection, _connection_record) -> None:
        cursor = dbapi_connection.cursor()
        try:
            cursor.execute(f"PRAGMA busy_timeout={SQLITE_BUSY_TIMEOUT_MS}")
            cursor.execute("PRAGMA journal_mode=WAL")
        finally:
            cursor.close()

    @event.listens_for(engine.sync_engine, "connect")
    def set_sqlite_connection_pragmas(dbapi_connection, _connection_record) -> None:
        cursor = dbapi_connection.cursor()
        try:
            cursor.execute(f"PRAGMA busy_timeout={SQLITE_BUSY_TIMEOUT_MS}")
            cursor.execute("PRAGMA synchronous=NORMAL")
        finally:
            cursor.close()


def is_sqlite_corruption_error(exc: BaseException) -> bool:
    """Return whether an exception indicates SQLite file-level corruption.

    Args:
        exc: Exception to inspect.

    Returns:
        Whether reconnecting to the current SQLite file is required.
    """
    if isinstance(exc, DBAPIError):
        return _contains_sqlite_corruption_marker(exc)
    return any(
        _contains_sqlite_corruption_marker(error) for error in _exception_chain(exc)
    )


def _exception_chain(exc: BaseException) -> tuple[BaseException, ...]:
    chain: list[BaseException] = []
    current: BaseException | None = exc
    while current is not None:
        chain.append(current)
        current = current.__cause__ or current.__context__
    return tuple(chain)


def _contains_sqlite_corruption_marker(exc: BaseException) -> bool:
    message = str(exc).lower()
    return any(marker in message for marker in SQLITE_CORRUPTION_ERROR_MARKERS)
