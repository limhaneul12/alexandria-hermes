"""SQLAlchemy implementation of Context Vault repository operations."""

from __future__ import annotations

from datetime import UTC, datetime

from app.memory.domain.contracts.context_contracts import (
    ContextAccessCreate,
    ContextChunkEmbeddingUpdate,
)
from app.memory.domain.contracts.context_recall_contracts import (
    ContextFtsRecall,
    ContextVectorRecall,
)
from app.memory.domain.entities.context_read_models import (
    ContextAccessEventRecord,
    ContextChunkRecord,
    ContextEmbeddingSourceStatus,
    ContextRecord,
    ContextSearchMatch,
)
from app.memory.domain.event_enum.context_enums import (
    ContextKind,
    ContextScope,
    RagHealthState,
)
from app.memory.domain.repositories.context_repository import IContextRepository
from app.memory.infrastructure.models.context_models import ContextChunkORM, ContextORM
from app.memory.infrastructure.repositories.contexts.access_events import (
    list_context_access_events,
    record_context_access,
)
from app.memory.infrastructure.repositories.contexts.deletion import delete_context_rows
from app.memory.infrastructure.repositories.contexts.embedding_reindex import (
    chunks_missing_embeddings,
    embedding_index_status,
    embedding_source_status,
    update_chunk_embeddings,
)
from app.memory.infrastructure.repositories.contexts.filters import (
    filtered_context_statement,
)
from app.memory.infrastructure.repositories.contexts.fts import (
    ensure_context_chunk_fts_table,
)
from app.memory.infrastructure.repositories.contexts.fts_search import (
    search_context_fts,
)
from app.memory.infrastructure.repositories.contexts.mapping import (
    map_chunk_row,
    map_context_row,
)
from app.memory.infrastructure.repositories.contexts.vector_search import (
    search_context_vectors,
)
from app.shared.exceptions import MemoryContextNotFoundError
from app.shared.types.extra_types import JSONObject
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession


class SqlAlchemyContextRepository(IContextRepository):
    """Concrete repository for Context Vault persistence and FTS retrieval."""

    def __init__(self, *, session: AsyncSession) -> None:
        self._session = session

    async def ensure_search_tables(self) -> None:
        """Create virtual search tables for FTS retrieval.

        Returns:
            None.
        """
        await ensure_context_chunk_fts_table(session=self._session)

    async def get(self, context_id: str) -> ContextRecord | None:
        """Return one context by primary key.

        Args:
            context_id: Context identifier.

        Returns:
            Stored context read model when found.
        """
        model = await self._session.get(ContextORM, context_id)
        context = None if model is None else map_context_row(model)
        return context

    async def list_all(
        self,
        *,
        limit: int,
        offset: int,
        kind: ContextKind | None = None,
        project: str | None = None,
        scope: ContextScope | None = None,
        workspace_id: str | None = None,
        agent_id: str | None = None,
        user_id: str | None = None,
        session_id: str | None = None,
        source_agent: str | None = None,
        tag: str | None = None,
        created_after: datetime | None = None,
        created_before: datetime | None = None,
        updated_after: datetime | None = None,
        updated_before: datetime | None = None,
        include_archived: bool = False,
    ) -> tuple[list[ContextRecord], int]:
        """List contexts with simple filters.

        Args:
            limit: Maximum returned entries.
            offset: Pagination offset.
            kind: Optional context kind filter.
            project: Optional project filter.
            scope: Optional scope filter.
            workspace_id: Optional workspace filter.
            agent_id: Optional agent filter.
            user_id: Optional user filter.
            session_id: Optional session filter.
            source_agent: Optional source-agent filter.
            tag: Optional tag filter.
            created_after: Optional inclusive created-at lower bound.
            created_before: Optional inclusive created-at upper bound.
            updated_after: Optional inclusive updated-at lower bound.
            updated_before: Optional inclusive updated-at upper bound.
            include_archived: Whether archived entries are included.

        Returns:
            Matching context rows and total count before pagination.
        """
        statement = filtered_context_statement(
            kind=kind,
            project=project,
            scope=scope,
            workspace_id=workspace_id,
            agent_id=agent_id,
            user_id=user_id,
            session_id=session_id,
            source_agent=source_agent,
            tag=tag,
            created_after=created_after,
            created_before=created_before,
            updated_after=updated_after,
            updated_before=updated_before,
            include_archived=include_archived,
        )
        count = await self._session.scalar(
            select(func.count()).select_from(statement.subquery())
        )
        page = (
            statement.order_by(ContextORM.updated_at.desc()).limit(limit).offset(offset)
        )
        rows = await self._session.execute(page)
        result = [map_context_row(row) for row in rows.scalars().all()], int(count or 0)
        return result

    async def chunks(self, context_id: str) -> list[ContextChunkRecord]:
        """Return chunks for one context.

        Args:
            context_id: Context identifier.

        Returns:
            Stored chunks for the context.
        """
        rows = await self._session.execute(
            select(ContextChunkORM)
            .where(ContextChunkORM.context_id == context_id)
            .order_by(ContextChunkORM.chunk_index)
        )
        chunks = [map_chunk_row(row) for row in rows.scalars().all()]
        return chunks

    async def archive(self, context_id: str) -> ContextRecord:
        """Archive one context instead of deleting it.

        Args:
            context_id: Context identifier.

        Returns:
            Archived context read model.
        """
        model = await self._require_context(context_id)
        archived_at = datetime.now(UTC)
        model.is_archived = True
        model.archived_at = archived_at
        model.updated_at = archived_at
        await self._session.flush()
        context = map_context_row(model)
        return context

    async def delete(self, context_id: str) -> None:
        model = await self._require_context(context_id)
        await delete_context_rows(
            session=self._session, context_id=context_id, model=model
        )

    async def record_access(self, payload: ContextAccessCreate) -> ContextRecord:
        """Record a recall/access event.

        Args:
            payload: Context access event fields.

        Returns:
            Updated context read model.
        """
        model = await self._require_context(payload.context_id)
        context = await record_context_access(
            session=self._session,
            model=model,
            payload=payload,
        )
        return context

    async def access_events(
        self, *, context_id: str, limit: int = 5
    ) -> list[ContextAccessEventRecord]:
        """Return recent access events for one context.

        Args:
            context_id: Context identifier.
            limit: Maximum event rows to return.

        Returns:
            Recent context access events, newest first.
        """
        await self._require_context(context_id)
        events = await list_context_access_events(
            session=self._session,
            context_id=context_id,
            limit=limit,
        )
        return events

    async def search_fts(self, recall: ContextFtsRecall) -> list[ContextSearchMatch]:
        """Search context chunks with SQLite FTS5.

        Args:
            recall: Validated FTS query and recall filters.

        Returns:
            Ranked context matches.
        """
        await self.ensure_search_tables()
        matches = await search_context_fts(self._session, recall)
        return matches

    async def search_vector(
        self, recall: ContextVectorRecall
    ) -> list[ContextSearchMatch]:
        """Search context chunks by sqlite-vec cosine distance.

        Args:
            recall: Validated vector query and recall filters.

        Returns:
            Ranked vector matches.
        """
        matches = await search_context_vectors(self._session, recall)
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
        """Return chunks missing embeddings or selected for forced rebuild.

        Args:
            model_name: Current embedding model name.
            dimensions: Current embedding dimensions.
            fingerprint_key: Current embedding generation fingerprint key.
            limit: Maximum chunks to scan.
            force: Whether to rebuild existing embeddings even if model metadata matches.

        Returns:
            Chunks requiring embedding backfill or forced rebuild.
        """
        chunks = await chunks_missing_embeddings(
            session=self._session,
            model_name=model_name,
            dimensions=dimensions,
            fingerprint_key=fingerprint_key,
            limit=limit,
            force=force,
        )
        return chunks

    async def embedding_index_status(
        self,
        *,
        model_name: str,
        dimensions: int,
        fingerprint_key: str,
    ) -> RagHealthState:
        """Return whether context chunk embeddings match the current fingerprint.

        Args:
            model_name: Current embedding model name.
            dimensions: Current embedding dimensions.
            fingerprint_key: Current embedding generation fingerprint key.

        Returns:
            HEALTHY when chunks match, otherwise REINDEX_REQUIRED.
        """
        status = await embedding_index_status(
            session=self._session,
            model_name=model_name,
            dimensions=dimensions,
            fingerprint_key=fingerprint_key,
        )
        return status

    async def embedding_source_status(
        self,
        *,
        model_name: str,
        dimensions: int,
        fingerprint_key: str,
        current_fingerprint: JSONObject,
    ) -> ContextEmbeddingSourceStatus:
        """Return source-level embedding fingerprint diagnostics.

        Args:
            model_name: Current embedding model name.
            dimensions: Current embedding dimensions.
            fingerprint_key: Current embedding generation fingerprint key.
            current_fingerprint: Current timestamp-free fingerprint payload.

        Returns:
            Context Vault embedding diagnostics.
        """
        status = await embedding_source_status(
            session=self._session,
            source_name="context_vault",
            model_name=model_name,
            dimensions=dimensions,
            fingerprint_key=fingerprint_key,
            current_fingerprint=current_fingerprint,
        )
        return status

    async def update_chunk_embeddings(
        self,
        updates: list[ContextChunkEmbeddingUpdate],
    ) -> int:
        """Persist context chunk embedding updates.

        Args:
            updates: Embedding updates keyed by chunk identifier.

        Returns:
            Number of chunks updated.
        """
        updated = await update_chunk_embeddings(
            session=self._session,
            updates=updates,
        )
        return updated

    async def _require_context(self, context_id: str) -> ContextORM:
        model = await self._session.get(ContextORM, context_id)
        if model is None:
            raise MemoryContextNotFoundError(f"Context not found: {context_id}")
        return model
