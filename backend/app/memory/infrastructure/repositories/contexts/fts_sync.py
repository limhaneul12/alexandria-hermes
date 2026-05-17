"""FTS synchronization helpers for Context Vault chunks."""

from __future__ import annotations

from app.memory.infrastructure.models.context_models import ContextChunkORM, ContextORM
from app.memory.infrastructure.repositories.contexts.fts import (
    delete_chunk_fts_statement,
    delete_context_fts_statement,
    ensure_context_chunk_fts_table,
    insert_chunk_fts_statement,
)
from sqlalchemy.ext.asyncio import AsyncSession


async def upsert_chunk_fts(
    *,
    session: AsyncSession,
    context: ContextORM,
    chunk: ContextChunkORM,
) -> None:
    """Synchronize one context chunk into the SQLite FTS table.

    Args:
        session: Active async database session.
        context: Parent context row.
        chunk: Chunk row to index.

    Returns:
        None.
    """
    await session.execute(delete_chunk_fts_statement(), {"chunk_id": chunk.id})
    await session.execute(
        insert_chunk_fts_statement(),
        {
            "chunk_id": chunk.id,
            "context_id": context.id,
            "title": context.title,
            "summary": context.summary,
            "content": chunk.content,
            "kind": context.kind,
            "project": context.project or "",
            "source_agent": context.source_agent,
            "tags": " ".join(str(tag) for tag in context.tags),
            "scope": context.scope,
            "workspace_id": context.workspace_id or "",
            "agent_id": context.agent_id or "",
            "user_id": context.user_id or "",
            "session_id": context.session_id or "",
            "heading": chunk.heading or "",
        },
    )


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
