"""FTS cleanup helpers for Context Vault chunks."""

from __future__ import annotations

from app.memory.infrastructure.repositories.contexts.fts import (
    delete_context_fts_statement,
    ensure_context_chunk_fts_table,
)
from sqlalchemy.ext.asyncio import AsyncSession


async def remove_context_fts(*, session: AsyncSession, context_id: str) -> None:
    """Remove all FTS rows for one context.

    Args:
        session: Active async database session.
        context_id: Context identifier to remove from FTS.

    Returns:
        None.
    """
    await ensure_context_chunk_fts_table(session=session)
    await session.execute(delete_context_fts_statement(), {"context_id": context_id})
