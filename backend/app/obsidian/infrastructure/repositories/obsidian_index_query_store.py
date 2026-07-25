"""Obsidian index read, search, duplicate, and graph query store."""

from __future__ import annotations

from app.obsidian.domain.contracts.obsidian_contracts import (
    ObsidianContextDuplicateQuery,
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
from app.obsidian.infrastructure.models.obsidian_index_models import (
    ObsidianChunkORM,
    ObsidianEdgeORM,
    ObsidianFileORM,
)
from app.obsidian.infrastructure.repositories.obsidian_fts import (
    build_obsidian_fts_query,
)
from app.obsidian.infrastructure.repositories.obsidian_index_mapping import (
    add_related_result,
    matches_tags,
    note_from_model,
    obsidian_excerpt,
)
from app.obsidian.infrastructure.repositories.obsidian_index_row_cleanup import (
    get_obsidian_file_by_path,
)
from app.obsidian.infrastructure.repositories.obsidian_index_schema import (
    ensure_obsidian_index_search_tables,
)
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession


class ObsidianIndexQueryStore:
    """Read and search the rebuildable Obsidian index cache."""

    def __init__(self, session: AsyncSession) -> None:
        """Create the query store.

        Args:
            session: Active async database session.
        """
        self._session = session

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

    async def find_context_duplicate(
        self,
        query: ObsidianContextDuplicateQuery,
    ) -> ObsidianNote | None:
        """Return an indexed Context with the same scope identity and body hash.

        Args:
            query: Canonical duplicate lookup constraints.

        Returns:
            Existing duplicate Context when found.
        """
        frontmatter = ObsidianFileORM.frontmatter_json
        statement = select(ObsidianFileORM).where(
            ObsidianFileORM.note_id != query.excluded_note_id,
            ObsidianFileORM.alexandria_type == "context",
            ObsidianFileORM.index_status == ObsidianIndexStatus.INDEXED.value,
            func.upper(func.json_extract(frontmatter, "$.scope")) == query.scope,
            func.json_extract(frontmatter, "$.content_hash") == query.content_hash,
        )
        identity_filters = (
            ("project", query.project),
            ("workspace_id", query.workspace_id),
            ("agent_id", query.agent_id),
            ("user_id", query.user_id),
            ("session_id", query.session_id),
        )
        for field_name, field_value in identity_filters:
            column = func.json_extract(frontmatter, f"$.{field_name}")
            statement = statement.where(
                column.is_(None) if field_value is None else column == field_value
            )
        model = await self._session.scalar(statement.limit(1))
        return None if model is None else note_from_model(model)

    async def search(self, query: ObsidianSearchQuery) -> list[ObsidianSearchHit]:
        """Search notes using FTS and indexed metadata filters.

        Args:
            query: Search filters and query text.

        Returns:
            Ranked search hits.
        """
        await ensure_obsidian_index_search_tables(self._session)
        fts_query = build_obsidian_fts_query(
            query.query,
            limit=query.limit,
            alexandria_type=query.alexandria_type,
            excluded_alexandria_types=query.excluded_alexandria_types,
            project=query.project,
            tags=query.tags,
        )
        if fts_query is None:
            return await _recent_notes(self._session, query)
        rows = await self._session.execute(
            fts_query.statement, dict(fts_query.parameters)
        )
        hits: list[ObsidianSearchHit] = []
        for chunk_id, note_id, rank in rows.all():
            note = await self.get_by_id(str(note_id))
            if note is None:
                continue
            if note.index_status != ObsidianIndexStatus.INDEXED:
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


async def _recent_notes(
    session: AsyncSession,
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
    rows = await session.execute(statement)
    return [
        ObsidianSearchHit(
            note=note_from_model(model),
            excerpt=obsidian_excerpt(model.body),
            score=0.0,
        )
        for model in rows.scalars().all()
        if matches_tags(model.tags, query.tags)
    ]
