"""Shared asynchronous database bootstrap and session management."""

from __future__ import annotations

from collections.abc import AsyncGenerator, AsyncIterator
from contextlib import asynccontextmanager

from app.shared.infrastructure.database_session_scope import DatabaseSessionScope
from app.shared.infrastructure.sqlite_database_policy import (
    SQLITE_BUSY_TIMEOUT_MS,
    SQLITE_CORRUPTION_ERROR_MARKERS,
    ensure_sqlite_parent,
    install_sqlite_connection_pragmas,
    is_sqlite_corruption_error,
    sqlite_path_from_url,
)
from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

__all__ = (
    "SQLITE_BUSY_TIMEOUT_MS",
    "SQLITE_CORRUPTION_ERROR_MARKERS",
    "Base",
    "Database",
    "is_sqlite_corruption_error",
)


class Base(DeclarativeBase):
    """SQLAlchemy declarative base used by backend ORM models."""


class Database:
    """Coordinate database lifecycle while focused policies own local concerns.

    The public surface combines lifecycle, health, session-factory, and request
    session entrypoints because they share one SQLAlchemy engine lifecycle. SQLite
    policy and session-scope behavior remain delegated to focused collaborators.
    """

    def __init__(
        self,
        *,
        database_url: str,
        create_schema: bool = False,
    ) -> None:
        """Create database coordinator.

        Args:
            database_url: Async SQLAlchemy URL.
            create_schema: Create ORM tables directly for isolated tests.
        """
        self._database_url = database_url
        self._create_schema = create_schema
        self._sqlite_path = sqlite_path_from_url(database_url)
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
            install_sqlite_connection_pragmas(self.engine)
        self._session_factory = async_sessionmaker(
            self.engine,
            expire_on_commit=False,
            class_=AsyncSession,
        )
        self._session_scope = DatabaseSessionScope(
            owner_identity=id(self),
            session_factory=self._session_factory,
        )

    async def initialize(self) -> None:
        """Initialize the database connection lifecycle.

        Runtime schema creation remains Alembic-owned. Direct metadata creation is
        available only through the explicit test-only option.
        """
        ensure_sqlite_parent(self._sqlite_path)
        async with self.engine.begin() as connection:
            if not self._create_schema:
                await connection.execute(text("SELECT 1"))
                return
            await connection.run_sync(Base.metadata.create_all)

    async def shutdown(self) -> None:
        """Release SQLAlchemy resources."""
        await self.engine.dispose()

    async def ping(self) -> bool:
        """Check whether the async database connection is available.

        Returns:
            Whether a trivial query succeeded.
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

        Args:
            exc: Exception observed at a database boundary.

        Returns:
            Whether a SQLite recovery action was applied.
        """
        if self._sqlite_path is None or not is_sqlite_corruption_error(exc):
            return False
        await self.engine.dispose()
        return True

    @property
    def sqlite_path(self) -> str | None:
        """Return the local SQLite path when configured.

        Returns:
            SQLite file path for local file-backed URLs, otherwise ``None``.
        """
        return self._sqlite_path

    def session(self) -> AsyncSession:
        """Create or reuse a SQLAlchemy session.

        Returns:
            Request-bound session when present, otherwise a new session.
        """
        return self._session_scope.session()

    @asynccontextmanager
    async def request_session(self) -> AsyncIterator[AsyncSession]:
        """Bind one managed session to the current request context.

        Yields:
            Session shared by repositories created during one request.
        """
        async with self._session_scope.request_session() as session:
            yield session

    def session_factory(self) -> async_sessionmaker[AsyncSession]:
        """Return the configured async session factory.

        Returns:
            Configured async SQLAlchemy session maker.
        """
        return self._session_scope.session_factory()

    async def get_session(self) -> AsyncGenerator[AsyncSession]:
        """Yield a managed session for FastAPI dependency injection.

        Yields:
            Managed async SQLAlchemy session.
        """
        async for session in self._session_scope.get_session():
            yield session
