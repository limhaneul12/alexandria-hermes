"""Obsidian vault search source for Context RAG retrieval."""

from __future__ import annotations

from collections.abc import Sequence
from typing import cast

from app.memory.application.retrieval.vector_serialization import (
    cosine_distance_to_score,
    vector_to_sqlite_json,
)
from app.memory.domain.contracts.context_contracts import ContextChunkEmbeddingUpdate
from app.memory.domain.contracts.context_recall_contracts import (
    ContextFtsRecall,
    ContextVectorRecall,
    ScopeIdentity,
)
from app.memory.domain.entities.context_read_models import (
    ContextChunkRecord,
    ContextEmbeddingSourceStatus,
    ContextSearchMatch,
)
from app.memory.domain.event_enum.context_enums import (
    ContextRecallLifecycleStatus,
    RagHealthState,
)
from app.memory.domain.repositories.context_search_source import IContextSearchSource
from app.memory.infrastructure.repositories.contexts.obsidian_context_mapping import (
    DEFAULT_EXCLUDED_OBSIDIAN_RECALL_PREFIXES,
    chunk_record_from_obsidian_row,
    match_from_obsidian_rows,
    matches_context_filters,
    raw_obsidian_chunk_id,
)
from app.memory.infrastructure.repositories.contexts.scope_recall_filter import (
    ScopeRecallColumns,
    scope_recall_clause,
)
from app.memory.infrastructure.repositories.contexts.sqlite_vec_connection import (
    load_sqlite_vec_for_session,
)
from app.obsidian.domain.event_enum.obsidian_enums import (
    AlexandriaNoteType,
    ObsidianIndexStatus,
)
from app.obsidian.infrastructure.models.obsidian_index_models import (
    ObsidianChunkORM,
    ObsidianFileORM,
)
from app.obsidian.infrastructure.repositories.obsidian_fts import (
    OBSIDIAN_FILES_TABLE,
    build_obsidian_fts_query,
    ensure_obsidian_chunk_fts_table,
)
from app.shared.types.extra_types import JSONObject
from sqlalchemy import bindparam, case, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.elements import ColumnElement

OBSIDIAN_MATCH_LIMIT_MULTIPLIER = 4


class SqlAlchemyObsidianContextSearchSource(IContextSearchSource):
    """Expose indexed Obsidian notes as a first-class Context RAG source."""

    def __init__(self, *, session: AsyncSession) -> None:
        self._session = session

    async def search_fts(self, recall: ContextFtsRecall) -> list[ContextSearchMatch]:
        """Search indexed Obsidian note chunks through SQLite FTS5.

        Args:
            recall: Validated FTS query and recall filters.

        Returns:
            Obsidian-backed matches mapped into Context RAG read models.
        """
        recall_filter = recall.recall_filter
        scope_filter = recall_filter.scope_identity
        await ensure_obsidian_chunk_fts_table(session=self._session)
        fts_query = build_obsidian_fts_query(
            recall.query,
            limit=_candidate_limit(recall_filter.limit),
            excluded_alexandria_types=[AlexandriaNoteType.LIBRARIAN_CHAT],
            included_statuses=list(
                ContextRecallLifecycleStatus.obsidian_values(
                    recall_filter.lifecycle_statuses
                )
            ),
            excluded_path_prefixes=list(DEFAULT_EXCLUDED_OBSIDIAN_RECALL_PREFIXES),
            project=None,
        )
        if fts_query is None:
            return []
        statement = fts_query.statement
        parameters = dict(fts_query.parameters)
        statement = statement.where(
            _obsidian_scope_recall_clause(
                OBSIDIAN_FILES_TABLE.c.frontmatter_json,
                OBSIDIAN_FILES_TABLE.c.project,
                scope_filter,
            )
        )
        parameters.update(scope_filter.sql_parameters())
        rows = await self._session.execute(statement, parameters)
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
                recall_filter.kind,
                scope_filter,
                project=scope_filter.project,
                include_lifecycle_statuses=recall_filter.lifecycle_statuses,
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
            if len(matches) >= recall_filter.limit:
                break
        return matches

    async def search_vector(
        self, recall: ContextVectorRecall
    ) -> list[ContextSearchMatch]:
        """Search indexed Obsidian note chunks through sqlite-vec.

        Args:
            recall: Validated vector query and recall filters.

        Returns:
            Obsidian-backed vector matches mapped into Context RAG read models.
        """
        recall_filter = recall.recall_filter
        scope_filter = recall_filter.scope_identity
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
                ObsidianChunkORM.embedding_fingerprint_key
                == bindparam("fingerprint_key"),
                *_recall_visibility_conditions(recall_filter.lifecycle_statuses),
            )
            .order_by(distance.asc())
            .limit(bindparam("limit"))
        )
        parameters: dict[str, str | int] = {
            "query_embedding": vector_to_sqlite_json(recall.query_embedding),
            "model_name": recall.model_name,
            "dimensions": recall.dimensions,
            "fingerprint_key": recall.fingerprint_key,
            "limit": _candidate_limit(recall_filter.limit),
        }
        obsidian_table = ObsidianFileORM.__table__
        statement = statement.where(
            _obsidian_scope_recall_clause(
                obsidian_table.c.frontmatter_json,
                obsidian_table.c.project,
                scope_filter,
            )
        )
        parameters.update(scope_filter.sql_parameters())
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
                recall_filter.kind,
                scope_filter,
                project=scope_filter.project,
                include_lifecycle_statuses=recall_filter.lifecycle_statuses,
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
            if len(matches) >= recall_filter.limit:
                break
        return matches

    async def chunks_missing_embeddings(
        self,
        *,
        model_name: str,
        dimensions: int,
        fingerprint_key: str,
        limit: int,
        force: bool = False,
    ) -> list[ContextChunkRecord]:
        """Return indexed Obsidian chunks missing current embedding metadata.

        Args:
            model_name: Current embedding model name.
            dimensions: Current embedding dimensions.
            fingerprint_key: Current embedding generation fingerprint key.
            limit: Maximum chunks to scan.
            force: Whether to rebuild existing embeddings even if metadata matches.

        Returns:
            Obsidian chunks mapped into Context RAG chunk read models.
        """
        statement = (
            select(ObsidianChunkORM)
            .join(ObsidianFileORM, ObsidianFileORM.note_id == ObsidianChunkORM.note_id)
            .where(*_default_recall_visibility_conditions())
            .where(func.length(func.trim(ObsidianChunkORM.text)) > 0)
            .limit(limit)
        )
        if not force:
            statement = statement.where(
                or_(
                    ObsidianChunkORM.embedding.is_(None),
                    ObsidianChunkORM.embedding_model != model_name,
                    ObsidianChunkORM.embedding_dimensions != dimensions,
                    ObsidianChunkORM.embedding_fingerprint_key.is_(None),
                    ObsidianChunkORM.embedding_fingerprint_key != fingerprint_key,
                )
            )
        statement = statement.order_by(
            case(
                (
                    (
                        ObsidianChunkORM.embedding.is_not(None)
                        & (ObsidianChunkORM.embedding_model == model_name)
                        & (ObsidianChunkORM.embedding_dimensions == dimensions)
                        & (
                            ObsidianChunkORM.embedding_fingerprint_key
                            == fingerprint_key
                        )
                    ),
                    1,
                ),
                else_=0,
            ).asc(),
            ObsidianChunkORM.embedding_indexed_at.asc().nulls_first(),
            ObsidianChunkORM.created_at.asc(),
        )
        rows = await self._session.execute(statement)
        chunks = [
            chunk_record_from_obsidian_row(chunk) for chunk in rows.scalars().all()
        ]
        return chunks

    async def embedding_index_status(
        self,
        *,
        model_name: str,
        dimensions: int,
        fingerprint_key: str,
    ) -> RagHealthState:
        """Return whether indexed Obsidian chunks match the current fingerprint.

        Args:
            model_name: Current embedding model name.
            dimensions: Current embedding dimensions.
            fingerprint_key: Current embedding generation fingerprint key.

        Returns:
            HEALTHY when chunks match, otherwise REINDEX_REQUIRED.
        """
        statement = (
            select(ObsidianChunkORM.id)
            .join(ObsidianFileORM, ObsidianFileORM.note_id == ObsidianChunkORM.note_id)
            .where(*_default_recall_visibility_conditions())
            .where(func.length(func.trim(ObsidianChunkORM.text)) > 0)
            .where(
                or_(
                    ObsidianChunkORM.embedding.is_(None),
                    ObsidianChunkORM.embedding_model != model_name,
                    ObsidianChunkORM.embedding_dimensions != dimensions,
                    ObsidianChunkORM.embedding_fingerprint_key.is_(None),
                    ObsidianChunkORM.embedding_fingerprint_key != fingerprint_key,
                )
            )
            .limit(1)
        )
        stale_chunk_id = await self._session.scalar(statement)
        if stale_chunk_id is None:
            return RagHealthState.HEALTHY
        return RagHealthState.REINDEX_REQUIRED

    async def embedding_source_status(
        self,
        *,
        model_name: str,
        dimensions: int,
        fingerprint_key: str,
        current_fingerprint: JSONObject,
    ) -> ContextEmbeddingSourceStatus:
        """Return source-level Obsidian embedding fingerprint diagnostics.

        Args:
            model_name: Current embedding model name.
            dimensions: Current embedding dimensions.
            fingerprint_key: Current embedding generation fingerprint key.
            current_fingerprint: Current timestamp-free fingerprint payload.

        Returns:
            Obsidian source embedding diagnostics.
        """
        total_rows = await self._session.scalar(
            select(func.count(ObsidianChunkORM.id))
            .join(ObsidianFileORM, ObsidianFileORM.note_id == ObsidianChunkORM.note_id)
            .where(*_default_recall_visibility_conditions())
            .where(func.length(func.trim(ObsidianChunkORM.text)) > 0)
        )
        current_rows = await self._session.scalar(
            select(func.count(ObsidianChunkORM.id))
            .join(ObsidianFileORM, ObsidianFileORM.note_id == ObsidianChunkORM.note_id)
            .where(
                *_default_recall_visibility_conditions(),
                func.length(func.trim(ObsidianChunkORM.text)) > 0,
                ObsidianChunkORM.embedding.is_not(None),
                ObsidianChunkORM.embedding_model == model_name,
                ObsidianChunkORM.embedding_dimensions == dimensions,
                ObsidianChunkORM.embedding_fingerprint_key == fingerprint_key,
            )
        )
        missing_rows = await self._session.scalar(
            select(func.count(ObsidianChunkORM.id))
            .join(ObsidianFileORM, ObsidianFileORM.note_id == ObsidianChunkORM.note_id)
            .where(
                *_default_recall_visibility_conditions(),
                func.length(func.trim(ObsidianChunkORM.text)) > 0,
                or_(
                    ObsidianChunkORM.embedding.is_(None),
                    ObsidianChunkORM.embedding_fingerprint_key.is_(None),
                ),
            )
        )
        fingerprint_rows = await self._session.execute(
            select(
                ObsidianChunkORM.embedding_provider,
                ObsidianChunkORM.embedding_model,
                ObsidianChunkORM.embedding_provider_version,
                ObsidianChunkORM.embedding_pooling_mode,
                ObsidianChunkORM.embedding_normalize,
                ObsidianChunkORM.embedding_dimensions,
            )
            .join(ObsidianFileORM, ObsidianFileORM.note_id == ObsidianChunkORM.note_id)
            .where(
                *_default_recall_visibility_conditions(),
                func.length(func.trim(ObsidianChunkORM.text)) > 0,
                ObsidianChunkORM.embedding_fingerprint_key.is_not(None),
            )
            .distinct()
        )
        total = int(total_rows or 0)
        current = int(current_rows or 0)
        stale = max(total - current, 0)
        missing = int(missing_rows or 0)
        return ContextEmbeddingSourceStatus(
            source_name="obsidian_vault",
            status=RagHealthState.HEALTHY
            if stale == 0
            else RagHealthState.REINDEX_REQUIRED,
            total_rows=total,
            current_rows=current,
            stale_rows=stale,
            missing_rows=missing,
            current_fingerprint=current_fingerprint,
            stored_fingerprints=[
                _fingerprint_payload(
                    provider=provider,
                    model=model,
                    provider_version=provider_version,
                    pooling_mode=pooling_mode,
                    normalize=normalize,
                    dimensions=stored_dimensions,
                )
                for (
                    provider,
                    model,
                    provider_version,
                    pooling_mode,
                    normalize,
                    stored_dimensions,
                ) in fingerprint_rows.all()
            ],
        )

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
            chunk.embedding_provider = update.embedding_provider
            chunk.embedding_provider_version = update.embedding_provider_version
            chunk.embedding_pooling_mode = update.embedding_pooling_mode
            chunk.embedding_normalize = update.embedding_normalize
            chunk.embedding_fingerprint_key = update.embedding_fingerprint_key
            chunk.embedding_fingerprint_json = update.embedding_fingerprint
            chunk.embedding_indexed_at = update.embedding_indexed_at
            updated += 1
        await self._session.flush()
        return updated


def _candidate_limit(limit: int) -> int:
    return max(limit, limit * OBSIDIAN_MATCH_LIMIT_MULTIPLIER)


def _obsidian_scope_recall_clause(
    frontmatter_column: ColumnElement[JSONObject],
    project_column: ColumnElement[str | None],
    scope_filter: ScopeIdentity,
) -> ColumnElement[bool]:
    scope_column = func.upper(func.json_extract(frontmatter_column, "$.scope"))
    workspace_id_column = func.json_extract(frontmatter_column, "$.workspace_id")
    agent_id_column = func.json_extract(frontmatter_column, "$.agent_id")
    user_id_column = func.json_extract(frontmatter_column, "$.user_id")
    session_id_column = func.json_extract(frontmatter_column, "$.session_id")
    return scope_recall_clause(
        ScopeRecallColumns(
            scope=scope_column,
            project=project_column,
            agent_id=agent_id_column,
            user_id=user_id_column,
            session_id=session_id_column,
            workspace_id=workspace_id_column,
        ),
        scope_filter,
    )


def _recall_visibility_conditions(
    include_lifecycle_statuses: Sequence[ContextRecallLifecycleStatus] | None,
) -> tuple[ColumnElement[bool], ...]:
    normalized_status = func.coalesce(
        func.nullif(func.lower(func.trim(ObsidianFileORM.status)), ""),
        "active",
    )
    return (
        ObsidianFileORM.index_status == ObsidianIndexStatus.INDEXED.value,
        ObsidianFileORM.alexandria_type != AlexandriaNoteType.LIBRARIAN_CHAT.value,
        normalized_status.in_(
            ContextRecallLifecycleStatus.obsidian_values(include_lifecycle_statuses)
        ),
        ~ObsidianFileORM.relative_path.like("\\_Ops/%", escape="\\"),
    )


def _default_recall_visibility_conditions() -> tuple[ColumnElement[bool], ...]:
    return _recall_visibility_conditions(None)


def _fingerprint_payload(
    *,
    provider: str | None,
    model: str | None,
    provider_version: str | None,
    pooling_mode: str | None,
    normalize: bool | None,
    dimensions: int | None,
) -> JSONObject:
    return {
        "provider": provider,
        "model": model,
        "provider_version": provider_version,
        "pooling_mode": pooling_mode,
        "normalize": normalize,
        "dimensions": dimensions,
    }
