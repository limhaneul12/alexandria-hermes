"""Shared asynchronous database bootstrap and session management."""

from __future__ import annotations

from collections.abc import AsyncGenerator, AsyncIterator
from contextlib import asynccontextmanager
from contextvars import ContextVar
from pathlib import Path
from urllib.parse import urlparse

from sqlalchemy import event, text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

_current_request_sessions: ContextVar[dict[int, AsyncSession] | None] = ContextVar(
    "current_request_sessions",
    default=None,
)


class Base(DeclarativeBase):
    """SQLAlchemy declarative base used by backend ORM models."""


SQLITE_BUSY_TIMEOUT_MS = 30_000
SQLITE_CORRUPTION_ERROR_MARKERS = (
    "database disk image is malformed",
    "file is not a database",
)


class Database:
    """Async SQLAlchemy database coordinator."""

    def __init__(
        self,
        *,
        database_url: str,
        create_schema: bool = False,
    ) -> None:
        """Create database coordinator.

        Args:
            database_url: Async SQLAlchemy URL.
            create_schema: Create ORM tables and FTS objects directly. This is
                intended for isolated tests; runtime schema is owned by Alembic.
        """
        self._database_url = database_url
        self._create_schema = create_schema
        self._sqlite_path = self._extract_sqlite_path()
        if self._sqlite_path is None:
            self.engine: AsyncEngine = create_async_engine(
                database_url,
                echo=False,
                future=True,
            )
        else:
            self.engine = create_async_engine(
                database_url,
                echo=False,
                future=True,
                connect_args={"timeout": SQLITE_BUSY_TIMEOUT_MS / 1000},
            )
        if self._sqlite_path is not None:
            self._install_sqlite_connection_pragmas()
        self._session_factory = async_sessionmaker(
            self.engine,
            expire_on_commit=False,
            class_=AsyncSession,
        )

    async def initialize(self) -> None:
        """Initialize the database connection lifecycle.

        Runtime schema creation is intentionally not performed here. Alembic
        owns application schema migrations; direct metadata creation is only
        available through the explicit test-only opt-in.
        """
        if self._sqlite_path is not None:
            Path(self._sqlite_path).parent.mkdir(parents=True, exist_ok=True)

        async with self.engine.begin() as connection:
            if not self._create_schema:
                await connection.execute(text("SELECT 1"))
                return

            await connection.run_sync(Base.metadata.create_all)

    def _install_sqlite_connection_pragmas(self) -> None:
        """Apply SQLite connection settings that prevent transient lock failures."""

        @event.listens_for(self.engine.sync_engine, "connect")
        def set_sqlite_pragmas(dbapi_connection, _connection_record) -> None:
            cursor = dbapi_connection.cursor()
            try:
                cursor.execute(f"PRAGMA busy_timeout={SQLITE_BUSY_TIMEOUT_MS}")
                cursor.execute("PRAGMA journal_mode=WAL")
                cursor.execute("PRAGMA synchronous=NORMAL")
            finally:
                cursor.close()

    async def shutdown(self) -> None:
        """Release SQLAlchemy resources."""
        await self.engine.dispose()

    async def ping(self) -> bool:
        """Check if the async database connection is available.

        Returns:
            bool: Value produced by ping.
        """
        try:
            async with self._session_factory() as session:
                await session.execute(text("SELECT 1"))
            return True
        except Exception as exc:
            await self.recover_from_error(exc)
            return False

    async def recover_from_error(self, exc: BaseException) -> bool:
        """Drop stale SQLite connections after file-level database failures.

        SQLite files are sometimes repaired or replaced while the local service is
        still running. SQLAlchemy can keep pooled connections to the old broken
        file handle, causing every later request to keep failing even after the
        on-disk database has been restored. Disposing the engine forces the next
        request to reconnect to the current file.

        Args:
            exc: Exception observed at a database boundary.

        Returns:
            True when a SQLite recovery action was applied.
        """
        if self._sqlite_path is None:
            return False
        if not is_sqlite_corruption_error(exc):
            return False
        await self.engine.dispose()
        return True

    @property
    def sqlite_path(self) -> str | None:
        """Return local SQLite path when the database URL targets a file.

        Returns:
            SQLite file path for local SQLite URLs, otherwise None.
        """
        return self._sqlite_path

    def session(self) -> AsyncSession:
        """Create a new SQLAlchemy session.

        Returns:
            Active request session when one is bound, otherwise a new AsyncSession.
        """
        current_sessions = _current_request_sessions.get()
        if (
            current_sessions is not None
            and (current_session := current_sessions.get(id(self))) is not None
        ):
            return current_session

        session = self._session_factory()
        return session

    @asynccontextmanager
    async def request_session(self) -> AsyncIterator[AsyncSession]:
        """Bind one managed session to the current request context.

        Yields:
            AsyncSession used by DI-created repositories during one request.
        """
        async with self._session_factory() as session:
            current_sessions = _current_request_sessions.get()
            next_sessions = {} if current_sessions is None else current_sessions.copy()
            next_sessions[id(self)] = session
            token = _current_request_sessions.set(next_sessions)
            try:
                yield session
            finally:
                _current_request_sessions.reset(token)

    def session_factory(self) -> async_sessionmaker[AsyncSession]:
        """Return the configured async session factory.

        Returns:
            async_sessionmaker[AsyncSession]: Value produced by session_factory.
        """
        return self._session_factory

    async def get_session(self) -> AsyncGenerator[AsyncSession]:
        """Yield a managed SQLAlchemy session for FastAPI dependencies.

        Yields:
            AsyncGenerator[AsyncSession]: Value produced by get_session.
        """
        async with self._session_factory() as session:
            yield session

    def _extract_sqlite_path(self) -> str | None:
        """Get a local filesystem path for sqlite URLs.

        Returns:
            Path string when url scheme is sqlite/aiosqlite.
        """
        parsed = urlparse(self._database_url)
        if parsed.scheme not in {"sqlite", "sqlite+aiosqlite"}:
            return None
        if parsed.path in {"", "/:memory:"}:
            return None
        if parsed.path.startswith("//"):
            return parsed.path[1:]
        return parsed.path.lstrip("/")


def is_sqlite_corruption_error(exc: BaseException) -> bool:
    """Return whether an exception indicates SQLite file-level corruption.

    Args:
        exc: Exception to inspect.

    Returns:
        True for DBAPI/SQLAlchemy corruption errors that require reconnecting.
    """
    if isinstance(exc, DBAPIError):
        return _contains_sqlite_corruption_marker(exc)
    return any(
        _contains_sqlite_corruption_marker(error) for error in _exception_chain(exc)
    )


def _exception_chain(exc: BaseException) -> tuple[BaseException, ...]:
    """Collect the explicit exception chain for marker inspection.

    Args:
        exc: Root exception.

    Returns:
        Tuple containing the root and chained exceptions.
    """
    chain: list[BaseException] = []
    current: BaseException | None = exc
    while current is not None:
        chain.append(current)
        current = current.__cause__ or current.__context__
    return tuple(chain)


def _contains_sqlite_corruption_marker(exc: BaseException) -> bool:
    message = str(exc).lower()
    return any(marker in message for marker in SQLITE_CORRUPTION_ERROR_MARKERS)
