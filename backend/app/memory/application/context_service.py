"""Application service for Context Vault linting and retrieval."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import replace
from datetime import datetime

from app.memory.application.context_lint import (
    ContextLintInput,
    ContextLintResult,
    lint_context,
)
from app.memory.application.retrieval.context_pack import build_context_pack
from app.memory.application.retrieval.context_ranking import (
    merge_hybrid_matches,
    rank_best_matches_per_context,
)
from app.memory.application.retrieval.embedding_provider import (
    EmbeddingProvider,
)
from app.memory.application.retrieval.rag_health import build_rag_dependency_health
from app.memory.application.retrieval.vector_serialization import vector_to_sqlite_json
from app.memory.domain.contracts.context_contracts import (
    ContextAccessCreate,
    ContextChunkEmbeddingUpdate,
)
from app.memory.domain.entities.context_read_models import (
    ContextAccessEventRecord,
    ContextChunkRecord,
    ContextPack,
    ContextRecord,
    ContextReindexResult,
    ContextSearchMatch,
    ContextSoftRebuildResult,
    RagDependencyHealth,
)
from app.memory.domain.event_enum.context_enums import (
    ContextAccessActorType,
    ContextAccessMethod,
    ContextKind,
    ContextScope,
    RagHealthState,
    RagStrategy,
)
from app.memory.domain.repositories.context_repository import IContextRepository
from app.memory.domain.repositories.context_search_source import IContextSearchSource
from app.shared.exceptions import (
    MemoryContextNotFoundError,
    MemoryContextValidationError,
)
from app.shared.types.types_convert_utils import enum_value, now_utc
from asyncer import asyncify


class ContextService:
    """Use cases for Context Vault linting and retrieval."""

    def __init__(
        self,
        repository: IContextRepository,
        embedding_provider: EmbeddingProvider | None = None,
        vector_retrieval_enabled: bool = False,
        extra_search_sources: Sequence[IContextSearchSource] | None = None,
    ) -> None:
        """Initialize service dependencies.

        Args:
            repository: Context persistence port.
            embedding_provider: Optional local embedding provider.
            vector_retrieval_enabled: Whether vector indexing and query paths are wired.
            extra_search_sources: Optional additional Context RAG sources.

        Returns:
            None.
        """
        self._repository = repository
        self._embedding_provider = embedding_provider
        self._vector_retrieval_enabled = vector_retrieval_enabled
        self._search_sources = [repository, *(extra_search_sources or ())]

    def lint(
        self,
        kind: ContextKind,
        title: str,
        content: str,
        summary: str | None,
        project: str | None,
        scope: ContextScope = ContextScope.PROJECT,
        workspace_id: str | None = None,
        agent_id: str | None = None,
        user_id: str | None = None,
        session_id: str | None = None,
        visibility: ContextScope = ContextScope.PROJECT,
        source_agent: str = "Hermes",
        tags: list[str] | None = None,
    ) -> ContextLintResult:
        """Run Context Harness linting without persistence.

        Args:
            kind: Context entry kind.
            title: Human-readable title.
            content: Markdown content.
            summary: Optional summary supplied by the caller.
            project: Optional project scope.
            scope: Recall-routing scope.
            workspace_id: Optional workspace identifier.
            agent_id: Optional agent identifier.
            user_id: Optional user identifier.
            session_id: Optional session identifier.
            visibility: Recall visibility scope.
            source_agent: Agent that produced the content.
            tags: Caller-provided tags.

        Returns:
            Context lint result with redaction and quality details.
        """
        kind = enum_value(kind, ContextKind, "kind")
        scope = enum_value(scope, ContextScope, "scope")
        visibility = enum_value(visibility, ContextScope, "visibility")
        result = lint_context(
            ContextLintInput(
                kind=kind,
                title=title,
                content=content,
                summary=summary,
                project=project,
                scope=scope,
                workspace_id=workspace_id,
                agent_id=agent_id,
                user_id=user_id,
                session_id=session_id,
                visibility=visibility,
                source_agent=source_agent,
                tags=[] if tags is None else tags,
            )
        )
        return result

    async def get(self, context_id: str) -> ContextRecord:
        """Return one context or raise not-found.

        Args:
            context_id: Context identifier.

        Returns:
            Stored context read model.
        """
        context = await self._repository.get(context_id)
        if context is None:
            raise MemoryContextNotFoundError(f"Context not found: {context_id}")
        return context

    async def list_contexts(
        self,
        limit: int = 50,
        offset: int = 0,
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
        """List contexts with filters.

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
        if kind is not None:
            kind = enum_value(kind, ContextKind, "kind")
        if scope is not None:
            scope = enum_value(scope, ContextScope, "scope")
        result = await self._repository.list_all(
            limit=limit,
            offset=offset,
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
        return result

    async def chunks(self, context_id: str) -> list[ContextChunkRecord]:
        """Return chunks for one context.

        Args:
            context_id: Context identifier.

        Returns:
            Stored chunks for the context.
        """
        await self.get(context_id)
        chunks = await self._repository.chunks(context_id)
        return chunks

    async def archive(self, context_id: str) -> ContextRecord:
        """Archive one context.

        Args:
            context_id: Context identifier.

        Returns:
            Archived context read model.
        """
        context = await self._repository.archive(context_id)
        return context

    async def delete(self, context_id: str) -> None:
        """Hard delete one context.

        Args:
            context_id: Context identifier.

        Returns:
            None.
        """
        await self._repository.delete(context_id)

    async def access(
        self,
        context_id: str,
        *,
        actor_name: str = "Alexandria UI",
        actor_type: ContextAccessActorType = ContextAccessActorType.UI,
        access_method: ContextAccessMethod = ContextAccessMethod.DETAIL_VIEW,
        source_surface: str | None = "context-detail",
    ) -> ContextRecord:
        """Record an access event.

        Args:
            context_id: Context identifier.
            actor_name: Actor label to store with the access event.
            actor_type: Actor category.
            access_method: Access method category.
            source_surface: Optional UI/tool surface that caused access.

        Returns:
            Updated context read model.
        """
        actor_type = enum_value(actor_type, ContextAccessActorType, "actor_type")
        access_method = enum_value(access_method, ContextAccessMethod, "access_method")
        context = await self._repository.record_access(
            ContextAccessCreate(
                context_id=context_id,
                accessed_at=now_utc(),
                actor_name=actor_name,
                actor_type=actor_type,
                access_method=access_method,
                source_surface=source_surface,
            )
        )
        return context

    async def access_events(
        self, context_id: str, limit: int = 5
    ) -> list[ContextAccessEventRecord]:
        """Return recent access events for one context.

        Args:
            context_id: Context identifier.
            limit: Maximum events to return.

        Returns:
            Recent access events ordered newest first.
        """
        events = await self._repository.access_events(
            context_id=context_id, limit=limit
        )
        return events

    def rag_health(self) -> RagDependencyHealth:
        """Return current RAG dependency health.

        Returns:
            Health state for FTS, vector, and embedding dependencies.
        """
        health = build_rag_dependency_health(
            embedding_provider=self._embedding_provider,
            vector_retrieval_enabled=self._vector_retrieval_enabled,
        )
        return health

    async def rag_health_with_index_status(self) -> RagDependencyHealth:
        """Return RAG health including persisted embedding fingerprint status.

        Returns:
            Health state that marks vector recall REINDEX_REQUIRED on mismatch.
        """
        health = self.rag_health()
        provider = self._embedding_provider
        if (
            provider is None
            or not self._vector_retrieval_enabled
            or health.vector is not RagHealthState.HEALTHY
            or health.embedding is not RagHealthState.HEALTHY
        ):
            return health

        index_status = await self._embedding_index_status(provider)
        if index_status is not RagHealthState.REINDEX_REQUIRED:
            return health

        warnings = [
            *health.warnings,
            (
                "Embedding index status is REINDEX_REQUIRED; vector recall "
                "is disabled across configured sources until all source "
                "fingerprints match; run retrieval reindex before vector recall."
            ),
        ]
        return replace(
            health,
            embedding=RagHealthState.REINDEX_REQUIRED,
            default_strategy=RagStrategy.FTS_ONLY,
            warnings=warnings,
        )

    async def search(
        self,
        query: str,
        strategy: RagStrategy = RagStrategy.HYBRID,
        limit: int = 5,
        project: str | None = None,
        kind: ContextKind | None = None,
        include_scopes: list[ContextScope] | None = None,
        workspace_id: str | None = None,
        agent_id: str | None = None,
        user_id: str | None = None,
        session_id: str | None = None,
    ) -> ContextPack:
        """Return a context pack for a query.

        Args:
            query: Search query text.
            strategy: Requested retrieval strategy.
            limit: Maximum matches.
            project: Optional project filter.
            kind: Optional context kind filter.
            include_scopes: Optional recall scope filters.
            workspace_id: Optional workspace filter.
            agent_id: Optional agent filter.
            user_id: Optional user filter.
            session_id: Optional session filter.

        Returns:
            Context pack containing retrieved matches and warnings.
        """
        if not query.strip():
            raise MemoryContextValidationError("query is required")
        strategy = enum_value(strategy, RagStrategy, "strategy")
        if kind is not None:
            kind = enum_value(kind, ContextKind, "kind")
        if include_scopes is not None:
            include_scopes = [
                enum_value(scope, ContextScope, "include_scopes")
                for scope in include_scopes
            ]
        health = await self.rag_health_with_index_status()
        effective = strategy
        warnings = list(health.warnings)
        if (
            strategy is RagStrategy.HYBRID
            and health.default_strategy is RagStrategy.FTS_ONLY
        ):
            effective = RagStrategy.FTS_ONLY
            warnings.append("Vector retrieval degraded; using FTS_ONLY.")
        if strategy is RagStrategy.VECTOR_ONLY and (
            health.vector is not RagHealthState.HEALTHY
            or health.embedding is not RagHealthState.HEALTHY
        ):
            effective = RagStrategy.FTS_ONLY
            warnings.append(
                "VECTOR_ONLY requested but vector dependencies are degraded; "
                "using FTS_ONLY."
            )
        if effective is RagStrategy.FTS_ONLY:
            matches = await self._search_fts_sources(
                query=query,
                limit=limit,
                project=project,
                kind=kind,
                include_scopes=include_scopes,
                workspace_id=workspace_id,
                agent_id=agent_id,
                user_id=user_id,
                session_id=session_id,
            )
        elif effective is RagStrategy.VECTOR_ONLY:
            matches = await self._search_vector_sources(
                query=query,
                limit=limit,
                project=project,
                kind=kind,
                include_scopes=include_scopes,
                workspace_id=workspace_id,
                agent_id=agent_id,
                user_id=user_id,
                session_id=session_id,
            )
        else:
            fts_matches = await self._search_fts_sources(
                query=query,
                limit=limit,
                project=project,
                kind=kind,
                include_scopes=include_scopes,
                workspace_id=workspace_id,
                agent_id=agent_id,
                user_id=user_id,
                session_id=session_id,
            )
            vector_matches = await self._search_vector_sources(
                query=query,
                limit=limit,
                project=project,
                kind=kind,
                include_scopes=include_scopes,
                workspace_id=workspace_id,
                agent_id=agent_id,
                user_id=user_id,
                session_id=session_id,
            )
            matches = merge_hybrid_matches(
                fts_matches=fts_matches,
                vector_matches=vector_matches,
                limit=limit,
            )
        recall_scopes = include_scopes or [ContextScope.PROJECT, ContextScope.GLOBAL]
        context_pack = ContextPack(
            query=query,
            strategy=strategy,
            effective_strategy=effective,
            warnings=warnings,
            recall_scopes=recall_scopes,
            matches=matches,
            context_pack=build_context_pack(query=query, matches=matches),
        )
        return context_pack

    async def reindex_embeddings(
        self, limit: int = 100, *, force: bool = False
    ) -> ContextReindexResult:
        """Backfill or rebuild embeddings for stored context chunks.

        Args:
            limit: Maximum chunks to reindex in this batch.
            force: Whether to rebuild existing embeddings even if model metadata matches.

        Returns:
            Context reindex result.
        """
        if limit < 1:
            raise MemoryContextValidationError("limit must be at least 1")
        provider = self._embedding_provider
        fingerprint = None if provider is None else provider.fingerprint()
        health = self.rag_health()
        warnings = list(health.warnings)
        if (
            provider is None
            or fingerprint is None
            or health.vector is not RagHealthState.HEALTHY
            or health.embedding is not RagHealthState.HEALTHY
        ):
            warnings.append("Vector dependencies are not healthy; reindex skipped.")
            return ContextReindexResult(
                scanned=0,
                updated=0,
                skipped=0,
                warnings=warnings,
            )

        processed_by_source: dict[int, set[str]] = {}
        fingerprint_key = fingerprint.key()
        scanned, updated = await _reindex_embedding_sources(
            sources=self._search_sources,
            provider=provider,
            fingerprint_key=fingerprint_key,
            limit=limit,
            force=False,
            processed_by_source=processed_by_source,
        )
        if force and scanned < limit:
            forced_scanned, forced_updated = await _reindex_embedding_sources(
                sources=self._search_sources,
                provider=provider,
                fingerprint_key=fingerprint_key,
                limit=limit - scanned,
                force=True,
                processed_by_source=processed_by_source,
            )
            scanned += forced_scanned
            updated += forced_updated
        result = ContextReindexResult(
            scanned=scanned,
            updated=updated,
            skipped=scanned - updated,
            warnings=warnings,
        )
        return result

    async def soft_rebuild_embeddings(
        self,
        limit: int = 100,
        *,
        verification_query: str | None = None,
        project: str | None = None,
    ) -> ContextSoftRebuildResult:
        """Rebuild embeddings without deleting source context/note/memory rows.

        Args:
            limit: Maximum chunks to rebuild in this batch.
            verification_query: Optional query to run after the rebuild.
            project: Optional project filter for the verification query.

        Returns:
            Operator-facing soft rebuild report.
        """
        before = await self.rag_health_with_index_status()
        reindex = await self.reindex_embeddings(limit=limit, force=True)
        after = await self.rag_health_with_index_status()
        verification_context_ids: list[str] = []
        verification_warnings: list[str] = []
        if verification_query is not None and verification_query.strip():
            verification = await self.search(
                query=verification_query,
                strategy=RagStrategy.HYBRID,
                limit=min(limit, 10),
                project=project,
            )
            verification_context_ids = list(
                dict.fromkeys(match.context.id for match in verification.matches)
            )
            verification_warnings = verification.warnings
        warnings = list(reindex.warnings)
        if after.embedding is RagHealthState.REINDEX_REQUIRED:
            warnings.append(
                "Soft rebuild batch incomplete; rerun with a higher limit or repeat "
                "until after.embedding is HEALTHY."
            )
        result = ContextSoftRebuildResult(
            mode="soft_embedding_vector_rebuild",
            source_preservation=(
                "Source contexts, Obsidian notes, and memory records are preserved; "
                "only chunk embedding metadata/vector fields are rewritten."
            ),
            hard_delete_performed=False,
            before=before,
            reindex=reindex,
            after=after,
            verification_query=verification_query,
            verification_matches=len(verification_context_ids),
            verification_context_ids=verification_context_ids,
            verification_warnings=verification_warnings,
            warnings=warnings,
        )
        return result

    async def _search_fts_sources(
        self,
        *,
        query: str,
        limit: int,
        project: str | None,
        kind: ContextKind | None,
        include_scopes: list[ContextScope] | None,
        workspace_id: str | None,
        agent_id: str | None,
        user_id: str | None,
        session_id: str | None,
    ) -> list[ContextSearchMatch]:
        matches: list[ContextSearchMatch] = []
        for source in self._search_sources:
            source_matches = await source.search_fts(
                query=query,
                limit=limit,
                project=project,
                kind=kind,
                include_scopes=include_scopes,
                workspace_id=workspace_id,
                agent_id=agent_id,
                user_id=user_id,
                session_id=session_id,
            )
            matches.extend(source_matches)
        return _rank_matches(matches, limit)

    async def _search_vector_sources(
        self,
        *,
        query: str,
        limit: int,
        project: str | None,
        kind: ContextKind | None,
        include_scopes: list[ContextScope] | None,
        workspace_id: str | None,
        agent_id: str | None,
        user_id: str | None,
        session_id: str | None,
    ) -> list[ContextSearchMatch]:
        provider = self._embedding_provider
        if provider is None:
            return []
        fingerprint = provider.fingerprint()
        query_embedding = await _embed_query(provider, query)
        if len(query_embedding) != provider.dimensions:
            raise MemoryContextValidationError(
                "Embedding provider returned an unexpected dimension"
            )
        matches: list[ContextSearchMatch] = []
        for source in self._search_sources:
            source_matches = await source.search_vector(
                query_embedding=query_embedding,
                model_name=provider.model_name,
                dimensions=provider.dimensions,
                fingerprint_key=fingerprint.key(),
                limit=limit,
                project=project,
                kind=kind,
                include_scopes=include_scopes,
                workspace_id=workspace_id,
                agent_id=agent_id,
                user_id=user_id,
                session_id=session_id,
            )
            matches.extend(source_matches)
        return _rank_matches(matches, limit)

    async def _embedding_index_status(
        self,
        provider: EmbeddingProvider,
    ) -> RagHealthState:
        fingerprint = provider.fingerprint()
        for source in self._search_sources:
            source_status = await source.embedding_index_status(
                model_name=provider.model_name,
                dimensions=provider.dimensions,
                fingerprint_key=fingerprint.key(),
            )
            if source_status is RagHealthState.REINDEX_REQUIRED:
                return source_status
        return RagHealthState.HEALTHY


async def _reindex_embedding_sources(
    *,
    sources: list[IContextSearchSource],
    provider: EmbeddingProvider,
    fingerprint_key: str,
    limit: int,
    force: bool,
    processed_by_source: dict[int, set[str]],
) -> tuple[int, int]:
    scanned = 0
    updated = 0
    for source_index, source in enumerate(sources):
        remaining = limit - scanned
        if remaining < 1:
            break
        processed_ids = processed_by_source.setdefault(source_index, set())
        chunks = await source.chunks_missing_embeddings(
            model_name=provider.model_name,
            dimensions=provider.dimensions,
            fingerprint_key=fingerprint_key,
            limit=remaining + len(processed_ids),
            force=force,
        )
        selected = [chunk for chunk in chunks if chunk.id not in processed_ids][
            :remaining
        ]
        if not selected:
            continue
        processed_ids.update(chunk.id for chunk in selected)
        scanned += len(selected)
        updates = await _embedding_updates(provider=provider, chunks=selected)
        updated += await source.update_chunk_embeddings(updates)
    return scanned, updated


async def _embed_documents(
    provider: EmbeddingProvider,
    texts: list[str],
) -> list[list[float]]:
    return await asyncify(provider.embed_documents, abandon_on_cancel=True)(texts)


async def _embed_query(provider: EmbeddingProvider, text: str) -> list[float]:
    return await asyncify(provider.embed_query, abandon_on_cancel=True)(text)


async def _embedding_updates(
    *,
    provider: EmbeddingProvider,
    chunks: list[ContextChunkRecord],
) -> list[ContextChunkEmbeddingUpdate]:
    if not chunks:
        return []
    embeddings = await _embed_documents(
        provider,
        [chunk.content for chunk in chunks],
    )
    if len(embeddings) != len(chunks):
        raise MemoryContextValidationError(
            "Embedding provider returned an unexpected vector count"
        )

    updates: list[ContextChunkEmbeddingUpdate] = []
    fingerprint = provider.fingerprint()
    indexed_at = now_utc()
    for chunk, embedding in zip(chunks, embeddings, strict=True):
        if len(embedding) != provider.dimensions:
            raise MemoryContextValidationError(
                "Embedding provider returned an unexpected dimension"
            )
        try:
            serialized = vector_to_sqlite_json(embedding)
        except ValueError as exc:
            raise MemoryContextValidationError(str(exc)) from exc
        updates.append(
            ContextChunkEmbeddingUpdate(
                chunk_id=chunk.id,
                embedding=serialized,
                embedding_model=provider.model_name,
                embedding_dimensions=provider.dimensions,
                embedding_provider=fingerprint.provider,
                embedding_provider_version=fingerprint.provider_version,
                embedding_pooling_mode=fingerprint.pooling_mode,
                embedding_normalize=fingerprint.normalize,
                embedding_fingerprint_key=fingerprint.key(),
                embedding_fingerprint=fingerprint.snapshot_payload(
                    indexed_at=indexed_at
                ),
                embedding_indexed_at=indexed_at,
            )
        )
    return updates


def _rank_matches(
    matches: list[ContextSearchMatch],
    limit: int,
) -> list[ContextSearchMatch]:
    return rank_best_matches_per_context(matches, limit)
