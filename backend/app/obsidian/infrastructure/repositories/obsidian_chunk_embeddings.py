"""Embedding preservation helpers for Obsidian chunk reindexing."""

from __future__ import annotations

from dataclasses import dataclass

from app.obsidian.infrastructure.models.obsidian_index_models import ObsidianChunkORM
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


@dataclass(frozen=True, slots=True)
class ExistingChunkEmbedding:
    """Embedding metadata preserved across unchanged Obsidian chunks."""

    embedding: str
    model: str
    dimensions: int


async def existing_chunk_embeddings(
    *,
    session: AsyncSession,
    note_id: str,
) -> dict[tuple[int, str], ExistingChunkEmbedding]:
    """Return existing embeddings keyed by stable chunk identity.

    Args:
        session: Active async database session.
        note_id: Note whose existing chunk embeddings should be inspected.

    Returns:
        Existing embeddings keyed by chunk index and content hash.
    """
    rows = await session.execute(
        select(ObsidianChunkORM).where(ObsidianChunkORM.note_id == note_id)
    )
    embeddings: dict[tuple[int, str], ExistingChunkEmbedding] = {}
    for chunk in rows.scalars().all():
        if (
            chunk.embedding is None
            or chunk.embedding_model is None
            or chunk.embedding_dimensions is None
        ):
            continue
        embeddings[(chunk.chunk_index, chunk.content_hash)] = ExistingChunkEmbedding(
            embedding=chunk.embedding,
            model=chunk.embedding_model,
            dimensions=chunk.embedding_dimensions,
        )
    return embeddings
