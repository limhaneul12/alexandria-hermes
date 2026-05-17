"""FTS search execution for Context Vault chunks."""

from __future__ import annotations

from app.memory.domain.entities.context_read_models import ContextSearchMatch
from app.memory.domain.event_enum.context_enums import ContextKind, ContextScope
from app.memory.infrastructure.models.context_models import ContextChunkORM, ContextORM
from app.memory.infrastructure.repositories.contexts.fts import build_context_fts_query
from app.memory.infrastructure.repositories.contexts.mapping import (
    map_chunk_row,
    map_context_row,
)
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


async def search_context_fts(
    *,
    session: AsyncSession,
    query: str,
    limit: int,
    project: str | None = None,
    kind: ContextKind | None = None,
    include_scopes: list[ContextScope] | None = None,
    workspace_id: str | None = None,
    agent_id: str | None = None,
    user_id: str | None = None,
    session_id: str | None = None,
) -> list[ContextSearchMatch]:
    """Search context chunks with SQLite FTS5.

    Args:
        session: Active async database session.
        query: Search query text.
        limit: Maximum returned matches.
        project: Optional project filter.
        kind: Optional context kind filter.
        include_scopes: Optional scope filters.
        workspace_id: Optional workspace filter.
        agent_id: Optional agent filter.
        user_id: Optional user filter.
        session_id: Optional session filter.

    Returns:
        Ranked context matches.
    """
    fts_query = build_context_fts_query(
        query,
        limit=limit,
        project=project,
        kind=kind,
        include_scopes=include_scopes,
        workspace_id=workspace_id,
        agent_id=agent_id,
        user_id=user_id,
        session_id=session_id,
    )
    if fts_query is None:
        return []
    rows = await session.execute(fts_query.statement, fts_query.parameters)
    ranked = [(str(row[0]), str(row[1]), float(row[2])) for row in rows.all()]
    if not ranked:
        return []

    chunk_ids = [chunk_id for chunk_id, _, _ in ranked]
    chunk_rows = await session.execute(
        select(ContextChunkORM).where(ContextChunkORM.id.in_(chunk_ids))
    )
    chunks_by_id = {row.id: row for row in chunk_rows.scalars().all()}
    context_ids = [context_id for _, context_id, _ in ranked]
    context_rows = await session.execute(
        select(ContextORM).where(ContextORM.id.in_(context_ids))
    )
    contexts_by_id = {row.id: row for row in context_rows.scalars().all()}

    matches: list[ContextSearchMatch] = []
    for chunk_id, context_id, rank in ranked:
        chunk_row = chunks_by_id.get(chunk_id)
        context_row = contexts_by_id.get(context_id)
        if chunk_row is None or context_row is None or context_row.is_archived:
            continue
        fts_score = 1.0 / (1.0 + abs(rank))
        matches.append(
            ContextSearchMatch(
                context=map_context_row(context_row),
                chunk=map_chunk_row(chunk_row),
                score=fts_score,
                fts_score=fts_score,
                vector_score=None,
                why_retrieved="Matched context chunk text with SQLite FTS5.",
            )
        )
    return matches
