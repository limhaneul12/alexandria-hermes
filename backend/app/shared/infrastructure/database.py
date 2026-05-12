"""Shared asynchronous database bootstrap and session management."""

from __future__ import annotations

from collections.abc import AsyncGenerator
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
    ) -> None:
        """Create database coordinator.

        Args:
            database_url: Async SQLAlchemy URL.
            fts_config: Configuration for the search virtual table.
        """
        self._database_url = database_url
        self._fts = fts_config
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
        """Initialize schema and bootstraps auxiliary objects."""
        database_path = self._extract_sqlite_path()
        if database_path is not None:
            Path(database_path).parent.mkdir(parents=True, exist_ok=True)

        async with self.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
            await connection.execute(text(self._fts.schema_sql))

    async def shutdown(self) -> None:
        """Release SQLAlchemy resources."""
        await self.engine.dispose()

    async def ping(self) -> bool:
        """Check if the async database connection is available."""
        try:
            async with self._session_factory() as session:
                await session.execute(text("SELECT 1"))
            return True
        except Exception:
            return False

    def session(self) -> AsyncSession:
        """Create a new SQLAlchemy session.

        Return:
            AsyncSession instance.
        """
        return self._session_factory()

    async def get_session(self) -> AsyncGenerator[AsyncSession]:
        """Yield a managed SQLAlchemy session for FastAPI dependencies."""
        async with self._session_factory() as session:
            yield session

    def _extract_sqlite_path(self) -> str | None:
        """Get a local filesystem path for sqlite URLs.

        Return:
            Path string when url scheme is sqlite/aiosqlite.
        """
        parsed = urlparse(self._database_url)
        if parsed.scheme not in {"sqlite", "sqlite+aiosqlite"}:
            return None
        if parsed.path in {"", "/:memory:"}:
            return None
        return parsed.path.lstrip("/")
