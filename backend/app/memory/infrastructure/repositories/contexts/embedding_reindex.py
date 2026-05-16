"""Embedding reindex persistence helpers for Context Vault chunks."""

from __future__ import annotations

from app.memory.domain.contracts.context_contracts import ContextChunkEmbeddingUpdate
from app.memory.domain.entities.context_read_models import ContextChunkRecord
from app.memory.infrastructure.models.context_models import ContextChunkORM, ContextORM
from app.memory.infrastructure.repositories.contexts.mapping import map_chunk_row
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession


async def chunks_missing_embeddings(
    *,
    session: AsyncSession,
    model_name: str,
    dimensions: int,
    limit: int,
) -> list[ContextChunkRecord]:
    """Return chunks missing embeddings for the current model.

    Args:
        session: Active async database session.
        model_name: Current embedding model name.
        dimensions: Current embedding dimensions.
        limit: Maximum chunks to scan.

    Returns:
        Chunks requiring embedding backfill.
    """
    rows = await session.execute(
        select(ContextChunkORM)
        .join(ContextORM, ContextORM.id == ContextChunkORM.context_id)
        .where(ContextORM.is_archived.is_(False))
        .where(
            or_(
                ContextChunkORM.embedding.is_(None),
                ContextChunkORM.embedding_model != model_name,
                ContextChunkORM.embedding_dimensions != dimensions,
            )
        )
        .order_by(ContextChunkORM.created_at.asc())
        .limit(limit)
    )
    chunks = [map_chunk_row(row) for row in rows.scalars().all()]
    return chunks


async def update_chunk_embeddings(
    *,
    session: AsyncSession,
    updates: list[ContextChunkEmbeddingUpdate],
) -> int:
    """Persist context chunk embedding updates.

    Args:
        session: Active async database session.
        updates: Embedding updates keyed by chunk identifier.

    Returns:
        Number of chunks updated.
    """
    updated = 0
    for update in updates:
        chunk = await session.get(ContextChunkORM, update.chunk_id)
        if chunk is None:
            continue
        chunk.embedding = update.embedding
        chunk.embedding_model = update.embedding_model
        chunk.embedding_dimensions = update.embedding_dimensions
        updated += 1
    await session.flush()
    return updated
