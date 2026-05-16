"""FTS synchronization helpers for Context Vault chunks."""

from __future__ import annotations

from app.memory.infrastructure.models.context_models import ContextChunkORM, ContextORM
from app.memory.infrastructure.repositories.contexts.fts import CONTEXT_CHUNK_FTS_SQL
from sqlalchemy import text
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
    await session.execute(
        text("DELETE FROM context_chunk_fts WHERE chunk_id = :chunk_id"),
        {"chunk_id": chunk.id},
    )
    await session.execute(
        text(
            """
            INSERT INTO context_chunk_fts(
                chunk_id, context_id, title, summary, content, kind, project,
                source_agent, tags, scope, workspace_id, agent_id, user_id,
                session_id, heading
            )
            VALUES (
                :chunk_id, :context_id, :title, :summary, :content, :kind,
                :project, :source_agent, :tags, :scope, :workspace_id, :agent_id,
                :user_id, :session_id, :heading
            )
            """
        ),
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
    await session.execute(text(CONTEXT_CHUNK_FTS_SQL))
    await session.execute(
        text("DELETE FROM context_chunk_fts WHERE context_id = :context_id"),
        {"context_id": context_id},
    )
