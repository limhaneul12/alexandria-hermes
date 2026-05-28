"""Obsidian vault search source for Context RAG retrieval."""

from __future__ import annotations

from typing import cast

from app.memory.domain.contracts.context_contracts import ContextChunkEmbeddingUpdate
from app.memory.domain.entities.context_read_models import (
    ContextChunkRecord,
    ContextSearchMatch,
)
from app.memory.domain.event_enum.context_enums import (
    ContextKind,
    ContextScope,
)
from app.memory.domain.repositories.context_search_source import IContextSearchSource
from app.memory.infrastructure.repositories.contexts.obsidian_context_mapping import (
    chunk_record_from_obsidian_row,
    match_from_obsidian_rows,
    matches_context_filters,
    metadata_filters_present,
    raw_obsidian_chunk_id,
)
from app.obsidian.domain.event_enum.obsidian_enums import ObsidianIndexStatus
from app.obsidian.infrastructure.models.obsidian_index_models import (
    ObsidianChunkORM,
    ObsidianFileORM,
)
from app.obsidian.infrastructure.repositories.obsidian_fts import (
    build_obsidian_fts_query,
    ensure_obsidian_chunk_fts_table,
)
from app.retrieval.application.vector_serialization import (
    cosine_distance_to_score,
    vector_to_sqlite_json,
)
from app.retrieval.infrastructure.sqlite_vec_connection import (
    load_sqlite_vec_for_session,
)
from sqlalchemy import bindparam, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.elements import ColumnElement

OBSIDIAN_MATCH_LIMIT_MULTIPLIER = 4


class SqlAlchemyObsidianContextSearchSource(IContextSearchSource):
    """Expose indexed Obsidian notes as a first-class Context RAG source."""

    def __init__(self, *, session: AsyncSession) -> None:
        self._session = session

    async def search_fts(
        self,
        *,
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
        """Search indexed Obsidian note chunks through SQLite FTS5.

        Args:
            query: Search query text.
            limit: Maximum returned matches.
            project: Optional project filter.
            kind: Optional Context RAG kind filter.
            include_scopes: Optional Context RAG scope filters.
            workspace_id: Optional workspace filter.
            agent_id: Optional agent filter.
            user_id: Optional user filter.
            session_id: Optional session filter.

        Returns:
            Obsidian-backed matches mapped into Context RAG read models.
        """
        if metadata_filters_present(
            workspace_id=workspace_id,
            agent_id=agent_id,
            user_id=user_id,
            session_id=session_id,
        ):
            return []
        await ensure_obsidian_chunk_fts_table(session=self._session)
        fts_query = build_obsidian_fts_query(
            query,
            limit=_candidate_limit(limit),
            project=project,
        )
        if fts_query is None:
            return []
        rows = await self._session.execute(fts_query.statement, fts_query.parameters)
        ranked = [(str(row[0]), str(row[1]), float(row[2])) for row in rows.all()]
        matches: list[ContextSearchMatch] = []
        for chunk_id, note_id, rank in ranked:
            note = await self._session.get(ObsidianFileORM, note_id)
            chunk = await self._session.get(ObsidianChunkORM, chunk_id)
            if note is None or chunk is None:
                continue
            if not chunk.text.strip():
                continue
            if not matches_context_filters(
                note,
                kind=kind,
                include_scopes=include_scopes,
            ):
                continue
            fts_score = 1.0 / (1.0 + abs(rank))
            matches.append(
                match_from_obsidian_rows(
                    note=note,
                    chunk=chunk,
                    score=fts_score,
                    fts_score=fts_score,
                    vector_score=None,
                    why_retrieved=(
                        "Matched Obsidian vault note chunk with SQLite FTS5."
                    ),
                )
            )
            if len(matches) >= limit:
                break
        return matches

    async def search_vector(
        self,
        *,
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
        """Search indexed Obsidian note chunks through sqlite-vec.

        Args:
            query_embedding: Query embedding vector.
            model_name: Embedding model that produced the query vector.
            dimensions: Expected embedding dimensions.
            limit: Maximum returned matches.
            project: Optional project filter.
            kind: Optional Context RAG kind filter.
            include_scopes: Optional Context RAG scope filters.
            workspace_id: Optional workspace filter.
            agent_id: Optional agent filter.
            user_id: Optional user filter.
            session_id: Optional session filter.

        Returns:
            Obsidian-backed vector matches mapped into Context RAG read models.
        """
        if metadata_filters_present(
            workspace_id=workspace_id,
            agent_id=agent_id,
            user_id=user_id,
            session_id=session_id,
        ):
            return []
        await load_sqlite_vec_for_session(self._session)
        distance = cast(
            ColumnElement[float],
            func.vec_distance_cosine(
                ObsidianChunkORM.embedding,
                bindparam("query_embedding"),
            ).label("distance"),
        )
        statement = (
            select(
                ObsidianChunkORM.id,
                ObsidianChunkORM.note_id,
                distance,
            )
            .join(ObsidianFileORM, ObsidianFileORM.note_id == ObsidianChunkORM.note_id)
            .where(
                ObsidianChunkORM.embedding.is_not(None),
                ObsidianChunkORM.embedding_model == bindparam("model_name"),
                ObsidianChunkORM.embedding_dimensions == bindparam("dimensions"),
                ObsidianFileORM.index_status == ObsidianIndexStatus.INDEXED.value,
            )
            .order_by(distance.asc())
            .limit(bindparam("limit"))
        )
        parameters: dict[str, str | int] = {
            "query_embedding": vector_to_sqlite_json(query_embedding),
            "model_name": model_name,
            "dimensions": dimensions,
            "limit": _candidate_limit(limit),
        }
        if project is not None:
            statement = statement.where(ObsidianFileORM.project == bindparam("project"))
            parameters["project"] = project
        rows = await self._session.execute(statement, parameters)
        ranked = [(str(row[0]), str(row[1]), float(row[2])) for row in rows.all()]
        matches: list[ContextSearchMatch] = []
        for chunk_id, note_id, distance_value in ranked:
            note = await self._session.get(ObsidianFileORM, note_id)
            chunk = await self._session.get(ObsidianChunkORM, chunk_id)
            if note is None or chunk is None:
                continue
            if not chunk.text.strip():
                continue
            if not matches_context_filters(
                note,
                kind=kind,
                include_scopes=include_scopes,
            ):
                continue
            vector_score = cosine_distance_to_score(distance_value)
            matches.append(
                match_from_obsidian_rows(
                    note=note,
                    chunk=chunk,
                    score=vector_score,
                    fts_score=None,
                    vector_score=vector_score,
                    why_retrieved=(
                        "Matched Obsidian vault note chunk with sqlite-vec "
                        "semantic embedding distance."
                    ),
                )
            )
            if len(matches) >= limit:
                break
        return matches

    async def chunks_missing_embeddings(
        self,
        *,
        model_name: str,
        dimensions: int,
        limit: int,
        force: bool = False,
    ) -> list[ContextChunkRecord]:
        """Return indexed Obsidian chunks missing current embedding metadata.

        Args:
            model_name: Current embedding model name.
            dimensions: Current embedding dimensions.
            limit: Maximum chunks to scan.
            force: Whether to rebuild existing embeddings even if metadata matches.

        Returns:
            Obsidian chunks mapped into Context RAG chunk read models.
        """
        statement = (
            select(ObsidianChunkORM)
            .join(ObsidianFileORM, ObsidianFileORM.note_id == ObsidianChunkORM.note_id)
            .where(ObsidianFileORM.index_status == ObsidianIndexStatus.INDEXED.value)
            .where(func.length(func.trim(ObsidianChunkORM.text)) > 0)
            .order_by(ObsidianChunkORM.created_at.asc())
            .limit(limit)
        )
        if not force:
            statement = statement.where(
                or_(
                    ObsidianChunkORM.embedding.is_(None),
                    ObsidianChunkORM.embedding_model != model_name,
                    ObsidianChunkORM.embedding_dimensions != dimensions,
                )
            )
        rows = await self._session.execute(statement)
        chunks = [
            chunk_record_from_obsidian_row(chunk) for chunk in rows.scalars().all()
        ]
        return chunks

    async def update_chunk_embeddings(
        self,
        updates: list[ContextChunkEmbeddingUpdate],
    ) -> int:
        """Persist embedding updates for indexed Obsidian chunks.

        Args:
            updates: Embedding updates keyed by prefixed Obsidian chunk id.

        Returns:
            Number of Obsidian chunks updated.
        """
        updated = 0
        for update in updates:
            chunk = await self._session.get(
                ObsidianChunkORM,
                raw_obsidian_chunk_id(update.chunk_id),
            )
            if chunk is None:
                continue
            chunk.embedding = update.embedding
            chunk.embedding_model = update.embedding_model
            chunk.embedding_dimensions = update.embedding_dimensions
            updated += 1
        await self._session.flush()
        return updated


def _candidate_limit(limit: int) -> int:
    return max(limit, limit * OBSIDIAN_MATCH_LIMIT_MULTIPLIER)
