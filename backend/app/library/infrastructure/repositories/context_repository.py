"""SQLAlchemy implementation of Context Vault repository operations."""

from __future__ import annotations

from datetime import UTC, datetime

from app.library.domain.contracts.context_contracts import (
    ContextChunkCreate,
    ContextCreate,
)
from app.library.domain.entities.context_read_models import (
    ContextChunkRecord,
    ContextRecord,
    ContextSearchMatch,
)
from app.library.domain.event_enum.context_enums import ContextKind
from app.library.domain.repositories.context_repository import IContextRepository
from app.library.infrastructure.models.context_models import (
    ContextChunkORM,
    ContextORM,
)
from app.library.infrastructure.repositories.contexts.fts import (
    CONTEXT_CHUNK_FTS_SQL,
    build_context_fts_query,
)
from app.library.infrastructure.repositories.contexts.mapping import (
    map_chunk_row,
    map_context_row,
)
from app.shared.exceptions import NotFoundError
from sqlalchemy import Select, func, select, text
from sqlalchemy.ext.asyncio import AsyncSession


class SqlAlchemyContextRepository(IContextRepository):
    """Concrete repository for Context Vault persistence and FTS retrieval."""

    def __init__(self, *, session: AsyncSession) -> None:
        """Initialize repository.

        Args:
            session: Active async session.
        """
        self._session = session

    async def ensure_search_tables(self) -> None:
        """Create virtual search tables for FTS retrieval.

        Returns:
            None.
        """
        await self._session.execute(text(CONTEXT_CHUNK_FTS_SQL))

    async def create(
        self,
        *,
        payload: ContextCreate,
        chunks: list[ContextChunkCreate],
    ) -> ContextRecord:
        """Persist a context and keep chunk FTS rows synchronized.

        Args:
            payload: Context fields to persist.
            chunks: Search chunks derived from the context content.

        Returns:
            Stored context read model.
        """
        await self.ensure_search_tables()
        model = ContextORM(
            kind=payload.kind.value,
            title=payload.title,
            summary=payload.summary,
            content=payload.content,
            content_format=payload.content_format.value,
            project=payload.project,
            source_agent=payload.source_agent,
            source_type=payload.source_type.value,
            importance=payload.importance.value,
            tags=payload.tags,
            status=payload.status.value,
            quality_score=payload.quality_score,
            warnings=payload.warnings,
            restore_prompt=payload.restore_prompt,
            context_metadata=payload.context_metadata,
            created_at=payload.created_at,
            updated_at=payload.updated_at,
            expires_at=payload.expires_at,
            access_count=0,
            is_archived=False,
        )
        self._session.add(model)
        await self._session.flush()

        chunk_rows = [
            ContextChunkORM(
                context_id=model.id,
                chunk_index=chunk.chunk_index,
                heading=chunk.heading,
                content=chunk.content,
                token_count=chunk.token_count,
                content_hash=chunk.content_hash,
                chunk_metadata=chunk.chunk_metadata,
                created_at=chunk.created_at,
            )
            for chunk in chunks
        ]
        self._session.add_all(chunk_rows)
        await self._session.flush()
        for chunk_row in chunk_rows:
            await self._upsert_chunk_fts(model, chunk_row)
        context = map_context_row(model)
        return context

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
        source_agent: str | None = None,
        tag: str | None = None,
        include_archived: bool = False,
    ) -> tuple[list[ContextRecord], int]:
        """List contexts with simple filters.

        Args:
            limit: Maximum returned entries.
            offset: Pagination offset.
            kind: Optional context kind filter.
            project: Optional project filter.
            source_agent: Optional source-agent filter.
            tag: Optional tag filter.
            include_archived: Whether archived entries are included.

        Returns:
            Matching context rows and total count before pagination.
        """
        statement = self._filtered_statement(
            kind=kind,
            project=project,
            source_agent=source_agent,
            tag=tag,
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
        await self._remove_fts_for_context(context_id)
        context = map_context_row(model)
        return context

    async def record_access(self, context_id: str) -> ContextRecord:
        """Record a recall/access event.

        Args:
            context_id: Context identifier.

        Returns:
            Updated context read model.
        """
        model = await self._require_context(context_id)
        model.last_accessed_at = datetime.now(UTC)
        model.access_count += 1
        await self._session.flush()
        context = map_context_row(model)
        return context

    async def search_fts(
        self,
        *,
        query: str,
        limit: int,
        project: str | None = None,
        kind: ContextKind | None = None,
    ) -> list[ContextSearchMatch]:
        """Search context chunks with SQLite FTS5.

        Args:
            query: Search query text.
            limit: Maximum returned matches.
            project: Optional project filter.
            kind: Optional context kind filter.

        Returns:
            Ranked context matches.
        """
        await self.ensure_search_tables()
        fts_query = build_context_fts_query(
            query,
            limit=limit,
            project=project,
            kind=kind,
        )
        if fts_query is None:
            return []
        rows = await self._session.execute(text(fts_query.sql), fts_query.parameters)
        ranked = [(str(row[0]), str(row[1]), float(row[2])) for row in rows.all()]
        if not ranked:
            return []
        chunk_ids = [chunk_id for chunk_id, _, _ in ranked]
        chunk_rows = await self._session.execute(
            select(ContextChunkORM).where(ContextChunkORM.id.in_(chunk_ids))
        )
        chunks_by_id = {row.id: row for row in chunk_rows.scalars().all()}
        context_ids = [context_id for _, context_id, _ in ranked]
        context_rows = await self._session.execute(
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

    def _filtered_statement(
        self,
        *,
        kind: ContextKind | None,
        project: str | None,
        source_agent: str | None,
        tag: str | None,
        include_archived: bool,
    ) -> Select[tuple[ContextORM]]:
        statement = select(ContextORM)
        if not include_archived:
            statement = statement.where(ContextORM.is_archived.is_(False))
        if kind is not None:
            statement = statement.where(ContextORM.kind == kind.value)
        if project is not None:
            statement = statement.where(ContextORM.project == project)
        if source_agent is not None:
            statement = statement.where(ContextORM.source_agent == source_agent)
        if tag is not None:
            statement = statement.where(
                text(
                    "EXISTS ("
                    "SELECT 1 FROM json_each(contexts.tags) "
                    "WHERE json_each.value = :context_tag"
                    ")"
                ).bindparams(context_tag=tag)
            )
        return statement

    async def _require_context(self, context_id: str) -> ContextORM:
        model = await self._session.get(ContextORM, context_id)
        if model is None:
            raise NotFoundError(f"Context not found: {context_id}")
        return model

    async def _upsert_chunk_fts(
        self,
        context: ContextORM,
        chunk: ContextChunkORM,
    ) -> None:
        await self._session.execute(
            text("DELETE FROM context_chunk_fts WHERE chunk_id = :chunk_id"),
            {"chunk_id": chunk.id},
        )
        await self._session.execute(
            text(
                """
                INSERT INTO context_chunk_fts(
                    chunk_id,
                    context_id,
                    title,
                    summary,
                    content,
                    kind,
                    project,
                    source_agent,
                    tags,
                    heading
                )
                VALUES (
                    :chunk_id,
                    :context_id,
                    :title,
                    :summary,
                    :content,
                    :kind,
                    :project,
                    :source_agent,
                    :tags,
                    :heading
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
                "heading": chunk.heading or "",
            },
        )

    async def _remove_fts_for_context(self, context_id: str) -> None:
        await self.ensure_search_tables()
        await self._session.execute(
            text("DELETE FROM context_chunk_fts WHERE context_id = :context_id"),
            {"context_id": context_id},
        )
