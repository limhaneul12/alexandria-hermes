"""Obsidian index search-table lifecycle."""

from __future__ import annotations

from app.obsidian.infrastructure.repositories.obsidian_fts import (
    ensure_obsidian_chunk_fts_table,
)
from sqlalchemy.ext.asyncio import AsyncSession


async def ensure_obsidian_index_search_tables(session: AsyncSession) -> None:
    """Create virtual search tables not represented by ORM metadata.

    Args:
        session: Active async database session.
    """
    await ensure_obsidian_chunk_fts_table(session=session)
