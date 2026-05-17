"""Vector search execution for Context Vault chunks."""

from __future__ import annotations

from app.memory.domain.entities.context_read_models import ContextSearchMatch
from app.memory.domain.event_enum.context_enums import ContextKind, ContextScope
from app.memory.infrastructure.models.context_models import ContextChunkORM, ContextORM
from app.memory.infrastructure.repositories.contexts.mapping import (
    map_chunk_row,
    map_context_row,
)
from app.memory.infrastructure.repositories.contexts.vector_query import (
    build_context_vector_query,
)
from app.retrieval.application.vector_serialization import (
    cosine_distance_to_score,
    vector_to_sqlite_json,
)
from app.retrieval.infrastructure.sqlite_vec_connection import (
    load_sqlite_vec_for_session,
)
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


async def search_context_vectors(
    *,
    session: AsyncSession,
    query_embedding: list[float],
    model_name: str,
    dimensions: int,
    limit: int,
    project: str | None = None,
    kind: ContextKind | None = None,
    include_scopes: list[ContextScope] | None = None,
    workspace_id: str | None = None,
    agent_id: str | None = None,
    user_id: str | None = None,
    session_id: str | None = None,
) -> list[ContextSearchMatch]:
    """Search context chunks by sqlite-vec cosine distance.

    Args:
        session: Active async database session.
        query_embedding: Query embedding vector.
        model_name: Embedding model that produced the query vector.
        dimensions: Expected embedding dimensions.
        limit: Maximum returned matches.
        project: Optional project filter.
        kind: Optional context kind filter.
        include_scopes: Optional scope filters.
        workspace_id: Optional workspace filter.
        agent_id: Optional agent filter.
        user_id: Optional user filter.
        session_id: Optional session filter.

    Returns:
        Ranked vector matches.
    """
    await load_sqlite_vec_for_session(session)
    vector_query = build_context_vector_query(
        query_embedding=vector_to_sqlite_json(query_embedding),
        model_name=model_name,
        dimensions=dimensions,
        limit=limit,
        project=project,
        kind=kind,
        include_scopes=include_scopes,
        workspace_id=workspace_id,
        agent_id=agent_id,
        user_id=user_id,
        session_id=session_id,
    )
    rows = await session.execute(vector_query.statement, vector_query.parameters)
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
    for chunk_id, context_id, distance in ranked:
        chunk_row = chunks_by_id.get(chunk_id)
        context_row = contexts_by_id.get(context_id)
        if chunk_row is None or context_row is None or context_row.is_archived:
            continue
        vector_score = cosine_distance_to_score(distance)
        matches.append(
            ContextSearchMatch(
                context=map_context_row(context_row),
                chunk=map_chunk_row(chunk_row),
                score=vector_score,
                fts_score=None,
                vector_score=vector_score,
                why_retrieved="Matched semantic embedding distance with sqlite-vec.",
            )
        )
    return matches
