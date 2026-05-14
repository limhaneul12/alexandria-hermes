"""Shared asynchronous database bootstrap and session management."""

from __future__ import annotations

from collections.abc import AsyncGenerator, AsyncIterator
from contextlib import asynccontextmanager
from contextvars import ContextVar
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse

from sqlalchemy import text
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


FTS_TABLE_SQL = """
CREATE VIRTUAL TABLE IF NOT EXISTS item_search_fts USING fts5(
    item_id UNINDEXED,
    item_type,
    title,
    summary,
    content,
    tags,
    details,
    tokenize='porter'
);
"""


@dataclass(frozen=True)
class SearchFTSConfig:
    """Configuration values for SQLite FTS5 search table."""

    table_name: str = "item_search_fts"
    schema_sql: str = FTS_TABLE_SQL.strip()


class Database:
    """Async SQLAlchemy database coordinator."""

    def __init__(
        self,
        *,
        database_url: str,
        fts_config: SearchFTSConfig = SearchFTSConfig(),
        create_schema: bool = False,
    ) -> None:
        """Create database coordinator.

        Args:
            database_url: Async SQLAlchemy URL.
            fts_config: Configuration for the search virtual table.
            create_schema: Create ORM tables and FTS objects directly. This is
                intended for isolated tests; runtime schema is owned by Alembic.
        """
        self._database_url = database_url
        self._fts = fts_config
        self._create_schema = create_schema
        self.engine: AsyncEngine = create_async_engine(
            database_url,
            echo=False,
            future=True,
        )
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
        database_path = self._extract_sqlite_path()
        if database_path is not None:
            Path(database_path).parent.mkdir(parents=True, exist_ok=True)

        async with self.engine.begin() as connection:
            if not self._create_schema:
                await connection.execute(text("SELECT 1"))
                return

            await connection.run_sync(Base.metadata.create_all)
            await connection.execute(text(self._fts.schema_sql))

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
        except Exception:
            return False

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
        return parsed.path.lstrip("/")
