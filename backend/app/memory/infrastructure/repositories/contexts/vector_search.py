"""Vector search execution for Context Vault chunks."""

from __future__ import annotations

from app.memory.application.retrieval.vector_serialization import (
    cosine_distance_to_score,
    vector_to_sqlite_json,
)
from app.memory.domain.contracts.context_recall_contracts import ContextVectorRecall
from app.memory.domain.entities.context_read_models import ContextSearchMatch
from app.memory.infrastructure.models.context_models import ContextChunkORM, ContextORM
from app.memory.infrastructure.repositories.contexts.mapping import (
    map_chunk_row,
    map_context_row,
)
from app.memory.infrastructure.repositories.contexts.sqlite_vec_connection import (
    load_sqlite_vec_for_session,
)
from app.memory.infrastructure.repositories.contexts.vector_query import (
    build_context_vector_query,
)
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


async def search_context_vectors(
    session: AsyncSession, recall: ContextVectorRecall
) -> list[ContextSearchMatch]:
    """Search context chunks by sqlite-vec cosine distance.

    Args:
        session: Active async database session.
        recall: Validated vector query and recall filters.

    Returns:
        Ranked vector matches.
    """
    await load_sqlite_vec_for_session(session)
    vector_query = build_context_vector_query(
        recall,
        vector_to_sqlite_json(recall.query_embedding),
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
        if chunk_row is None or context_row is None:
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
