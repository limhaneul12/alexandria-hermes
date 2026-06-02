"""SQLAlchemy repository for the rebuildable Obsidian index cache."""

from __future__ import annotations

from datetime import UTC, datetime

from app.obsidian.domain.contracts.obsidian_contracts import (
    ObsidianNoteIndex,
    ObsidianSearchQuery,
)
from app.obsidian.domain.entities.obsidian_note import (
    ObsidianNote,
    ObsidianRelatedNote,
    ObsidianSearchHit,
)
from app.obsidian.domain.event_enum.obsidian_enums import (
    ObsidianIndexStatus,
)
from app.obsidian.domain.repositories.obsidian_repository import (
    IObsidianIndexRepository,
)
from app.obsidian.infrastructure.models.obsidian_index_models import (
    ObsidianChunkORM,
    ObsidianEdgeORM,
    ObsidianFileORM,
)
from app.obsidian.infrastructure.repositories.obsidian_chunk_embeddings import (
    existing_chunk_embeddings,
)
from app.obsidian.infrastructure.repositories.obsidian_fts import (
    OBSIDIAN_CHUNK_FTS_TABLE,
    build_obsidian_fts_query,
    delete_obsidian_fts_statement,
    ensure_obsidian_chunk_fts_table,
)
from app.obsidian.infrastructure.repositories.obsidian_index_mapping import (
    add_related_result,
    matches_tags,
    note_from_model,
    obsidian_excerpt,
)
from app.obsidian.infrastructure.repositories.obsidian_index_row_cleanup import (
    discard_obsidian_note_index,
    get_obsidian_file_by_path,
)
from app.shared.infrastructure.identifiers import new_uuid
from app.shared.types.types_convert_utils import aware_utc_datetime
from sqlalchemy import delete, func, insert, or_, select
from sqlalchemy.ext.asyncio import AsyncSession


class SqlAlchemyObsidianIndexRepository(IObsidianIndexRepository):
    """Persist Obsidian search metadata in SQLite."""

    def __init__(self, *, session: AsyncSession) -> None:
        self._session = session

    async def ensure_search_tables(self) -> None:
        """Create virtual search tables for Obsidian search."""
        await ensure_obsidian_chunk_fts_table(session=self._session)

    async def upsert_note(self, payload: ObsidianNoteIndex) -> ObsidianNote:
        """Create or update one indexed note and its chunks.

        Args:
            payload: Indexed note payload.

        Returns:
            Persisted note entity.
        """
        await self.ensure_search_tables()
        now = datetime.now(UTC)
        path_model = await get_obsidian_file_by_path(
            self._session, payload.relative_path
        )
        model = await self._session.get(ObsidianFileORM, payload.note_id)
        if path_model is not None and path_model.note_id != payload.note_id:
            await discard_obsidian_note_index(self._session, path_model.note_id)
            await self._session.delete(path_model)
            await self._session.flush()
        if model is None:
            model = ObsidianFileORM(note_id=payload.note_id)
            self._session.add(model)
        model.relative_path = payload.relative_path
        model.alexandria_type = payload.alexandria_type.value
        model.title = payload.title
        model.status = payload.status
        model.tags = payload.tags
        model.project = payload.project
        model.source = payload.source
        model.content_hash = payload.content_hash
        model.frontmatter_json = payload.frontmatter
        model.body = payload.body
        model.index_status = ObsidianIndexStatus.INDEXED.value
        model.error_message = None
        model.size_bytes = payload.size_bytes
        model.modified_at = aware_utc_datetime(payload.modified_at)
        model.indexed_at = now
        await self._replace_chunks(payload, now=now)
        await self._replace_edges(payload, now=now)
        await self._session.flush()
        return note_from_model(model)

    async def mark_missing_stale(self, relative_paths: set[str]) -> int:
        """Mark missing indexed notes as stale.

        Args:
            relative_paths: Paths observed during the current scan.

        Returns:
            Number of notes marked stale.
        """
        statement = select(ObsidianFileORM).where(
            ObsidianFileORM.index_status != ObsidianIndexStatus.STALE.value
        )
        if relative_paths:
            statement = statement.where(
                ObsidianFileORM.relative_path.not_in(relative_paths)
            )
        rows = await self._session.execute(statement)
        stale = 0
        for model in rows.scalars().all():
            model.index_status = ObsidianIndexStatus.STALE.value
            model.indexed_at = datetime.now(UTC)
            stale += 1
        await self._session.flush()
        return stale

    async def get_by_id(self, note_id: str) -> ObsidianNote | None:
        """Read one indexed note by id.

        Args:
            note_id: Stable note id.

        Returns:
            Note entity when found.
        """
        model = await self._session.get(ObsidianFileORM, note_id)
        return None if model is None else note_from_model(model)

    async def get_by_path(self, relative_path: str) -> ObsidianNote | None:
        """Read one indexed note by vault-relative path.

        Args:
            relative_path: Vault-relative path.

        Returns:
            Note entity when found.
        """
        model = await get_obsidian_file_by_path(self._session, relative_path)
        return None if model is None else note_from_model(model)

    async def search(self, query: ObsidianSearchQuery) -> list[ObsidianSearchHit]:
        """Search notes using FTS and indexed metadata filters.

        Args:
            query: Search filters and query text.

        Returns:
            Ranked search hits.
        """
        await self.ensure_search_tables()
        fts_query = build_obsidian_fts_query(
            query.query,
            limit=query.limit,
            alexandria_type=query.alexandria_type,
            excluded_alexandria_types=query.excluded_alexandria_types,
            project=query.project,
            tags=query.tags,
        )
        if fts_query is None:
            return await self._recent_notes(query)
        rows = await self._session.execute(fts_query.statement, fts_query.parameters)
        hits: list[ObsidianSearchHit] = []
        for chunk_id, note_id, rank in rows.all():
            note = await self.get_by_id(str(note_id))
            if note is None:
                continue
            chunk = await self._session.get(ObsidianChunkORM, str(chunk_id))
            excerpt = obsidian_excerpt(chunk.text if chunk is not None else note.body)
            hits.append(
                ObsidianSearchHit(
                    note=note,
                    excerpt=excerpt,
                    score=float(rank),
                    chunk_id=str(chunk_id),
                    heading_path=None if chunk is None else chunk.heading_path,
                )
            )
        return hits

    async def related_notes(
        self,
        *,
        note_id: str,
        limit: int,
    ) -> list[ObsidianRelatedNote]:
        """Return ranked related notes from indexed graph edges.

        Args:
            note_id: Source or target note id to expand.
            limit: Maximum related notes.

        Returns:
            Ranked related-note results.
        """
        source = await self.get_by_id(note_id)
        if source is None:
            return []
        results: dict[str, ObsidianRelatedNote] = {}
        outgoing = await self._session.execute(
            select(ObsidianEdgeORM, ObsidianFileORM)
            .join(
                ObsidianFileORM,
                or_(
                    ObsidianFileORM.note_id == ObsidianEdgeORM.target_note_id,
                    ObsidianFileORM.relative_path == ObsidianEdgeORM.target_path,
                ),
            )
            .where(ObsidianEdgeORM.source_note_id == note_id)
        )
        for edge, note_model in outgoing.all():
            add_related_result(results, edge, note_model, direction="outgoing")
        incoming = await self._session.execute(
            select(ObsidianEdgeORM, ObsidianFileORM)
            .join(
                ObsidianFileORM,
                ObsidianFileORM.note_id == ObsidianEdgeORM.source_note_id,
            )
            .where(
                or_(
                    ObsidianEdgeORM.target_note_id == note_id,
                    ObsidianEdgeORM.target_path == source.relative_path,
                )
            )
        )
        for edge, note_model in incoming.all():
            add_related_result(results, edge, note_model, direction="incoming")
        ranked = sorted(results.values(), key=lambda item: item.score, reverse=True)
        return ranked[:limit]

    async def count_by_status(self) -> tuple[int, int, int]:
        """Return indexed, stale, and error note counts.

        Returns:
            Tuple of indexed, stale, and error note counts.
        """
        rows = await self._session.execute(
            select(ObsidianFileORM.index_status, func.count()).group_by(
                ObsidianFileORM.index_status
            )
        )
        counts = {str(status): int(count) for status, count in rows.all()}
        return (
            counts.get(ObsidianIndexStatus.INDEXED.value, 0),
            counts.get(ObsidianIndexStatus.STALE.value, 0),
            counts.get(ObsidianIndexStatus.ERROR.value, 0),
        )

    async def _replace_chunks(
        self,
        payload: ObsidianNoteIndex,
        *,
        now: datetime,
    ) -> None:
        with self._session.no_autoflush:
            existing_embeddings = await existing_chunk_embeddings(
                session=self._session,
                note_id=payload.note_id,
            )
        await self._session.execute(
            delete(ObsidianChunkORM).where(ObsidianChunkORM.note_id == payload.note_id)
        )
        await self._session.execute(
            delete_obsidian_fts_statement(),
            {"note_id": payload.note_id},
        )
        chunk_models: list[ObsidianChunkORM] = []
        fts_rows: list[dict[str, str]] = []
        for chunk in payload.chunks:
            chunk_id = new_uuid()
            embedding = existing_embeddings.get((chunk.chunk_index, chunk.content_hash))
            chunk_models.append(
                ObsidianChunkORM(
                    id=chunk_id,
                    note_id=payload.note_id,
                    chunk_index=chunk.chunk_index,
                    heading_path=chunk.heading_path,
                    text=chunk.text,
                    token_count=chunk.token_count,
                    content_hash=chunk.content_hash,
                    embedding=None if embedding is None else embedding.embedding,
                    embedding_model=None if embedding is None else embedding.model,
                    embedding_dimensions=None
                    if embedding is None
                    else embedding.dimensions,
                    embedding_provider=None
                    if embedding is None
                    else embedding.provider,
                    embedding_provider_version=None
                    if embedding is None
                    else embedding.provider_version,
                    embedding_pooling_mode=None
                    if embedding is None
                    else embedding.pooling_mode,
                    embedding_normalize=None
                    if embedding is None
                    else embedding.normalize,
                    embedding_fingerprint_key=None
                    if embedding is None
                    else embedding.fingerprint_key,
                    embedding_fingerprint_json=None
                    if embedding is None
                    else embedding.fingerprint,
                    embedding_indexed_at=None
                    if embedding is None
                    else embedding.indexed_at,
                    created_at=now,
                )
            )
            fts_rows.append(
                {
                    "chunk_id": chunk_id,
                    "note_id": payload.note_id,
                    "title": payload.title,
                    "body": chunk.text,
                    "heading_path": chunk.heading_path or "",
                    "alexandria_type": payload.alexandria_type.value,
                    "project": payload.project or "",
                    "status": payload.status,
                    "tags": " ".join(payload.tags),
                    "relative_path": payload.relative_path,
                }
            )
        self._session.add_all(chunk_models)
        if fts_rows:
            await self._session.execute(insert(OBSIDIAN_CHUNK_FTS_TABLE), fts_rows)

    async def _replace_edges(
        self,
        payload: ObsidianNoteIndex,
        *,
        now: datetime,
    ) -> None:
        await self._session.execute(
            delete(ObsidianEdgeORM).where(
                ObsidianEdgeORM.source_note_id == payload.note_id
            )
        )
        edge_models: list[ObsidianEdgeORM] = []
        for edge in payload.edges:
            target_note_id = edge.target_note_id
            if target_note_id is None:
                target = await self.get_by_path(edge.target_path)
                target_note_id = None if target is None else target.note_id
            edge_models.append(
                ObsidianEdgeORM(
                    edge_id=edge.edge_id,
                    source_note_id=edge.source_note_id,
                    source_path=edge.source_path,
                    target_note_id=target_note_id,
                    target_path=edge.target_path,
                    relation=edge.relation.value,
                    confidence=edge.confidence,
                    source_kind=edge.source_kind.value,
                    created_at=now,
                    indexed_at=now,
                )
            )
        self._session.add_all(edge_models)

    async def _recent_notes(
        self,
        query: ObsidianSearchQuery,
    ) -> list[ObsidianSearchHit]:
        statement = select(ObsidianFileORM).where(
            ObsidianFileORM.index_status == ObsidianIndexStatus.INDEXED.value
        )
        if query.alexandria_type is not None:
            statement = statement.where(
                ObsidianFileORM.alexandria_type == query.alexandria_type.value
            )
        if query.excluded_alexandria_types:
            statement = statement.where(
                ObsidianFileORM.alexandria_type.not_in(
                    [note_type.value for note_type in query.excluded_alexandria_types]
                )
            )
        if query.project is not None:
            statement = statement.where(ObsidianFileORM.project == query.project)
        statement = statement.order_by(ObsidianFileORM.modified_at.desc()).limit(
            query.limit
        )
        rows = await self._session.execute(statement)
        return [
            ObsidianSearchHit(
                note=note_from_model(model),
                excerpt=obsidian_excerpt(model.body),
                score=0.0,
            )
            for model in rows.scalars().all()
            if matches_tags(model.tags, query.tags)
        ]
