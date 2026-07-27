"""FTS and vector query store for Obsidian-backed Context recall."""

from __future__ import annotations

from typing import cast

from app.memory.application.retrieval.vector_serialization import (
    cosine_distance_to_score,
    vector_to_sqlite_json,
)
from app.memory.domain.contracts.context_recall_contracts import (
    ContextFtsRecall,
    ContextVectorRecall,
)
from app.memory.domain.entities.context_read_models import (
    ContextSearchMatch,
)
from app.memory.domain.event_enum.context_enums import (
    ContextRecallLifecycleStatus,
)
from app.memory.infrastructure.repositories.contexts.obsidian_context_mapping import (
    DEFAULT_EXCLUDED_OBSIDIAN_RECALL_PREFIXES,
    match_from_obsidian_rows,
    matches_context_filters,
)
from app.memory.infrastructure.repositories.contexts.obsidian_recall_policy import (
    _candidate_limit,
    _obsidian_scope_recall_clause,
    _recall_visibility_conditions,
)
from app.memory.infrastructure.repositories.contexts.sqlite_vec_connection import (
    load_sqlite_vec_for_session,
)
from app.obsidian.domain.event_enum.obsidian_enums import (
    AlexandriaNoteType,
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
from app.shared.infrastructure.sqlite_fts_relevance import (
    sqlite_fts_rank_to_score,
)
from sqlalchemy import bindparam, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.elements import ColumnElement


class ObsidianContextQueryStore:
    """Execute Obsidian-backed Context FTS and vector queries."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize the shared async database session.

        Args:
            session: Active async database session.
        """
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
            fts_score = sqlite_fts_rank_to_score(rank)
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
