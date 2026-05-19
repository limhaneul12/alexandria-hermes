"""Application service for Context Vault storage and retrieval."""

from __future__ import annotations

from datetime import datetime

from app.memory.application.context_compact import build_compact_context_content
from app.memory.application.context_lint import (
    ContextLintInput,
    ContextLintResult,
    lint_context,
)
from app.memory.application.harness_context import (
    build_harness_context_content,
    harness_context_metadata,
)
from app.memory.domain.contracts.context_contracts import (
    ContextAccessCreate,
    ContextChunkCreate,
    ContextChunkEmbeddingUpdate,
    ContextCreate,
)
from app.memory.domain.contracts.harness_contracts import HarnessCapture
from app.memory.domain.entities.context_read_models import (
    ContextAccessEventRecord,
    ContextChunkRecord,
    ContextPack,
    ContextRecord,
    ContextReindexResult,
    ContextSearchMatch,
    RagDependencyHealth,
)
from app.memory.domain.event_enum.context_enums import (
    ContextAccessActorType,
    ContextAccessMethod,
    ContextContentFormat,
    ContextImportance,
    ContextKind,
    ContextScope,
    ContextSourceType,
    ContextStorageStatus,
    RagHealthState,
    RagStrategy,
)
from app.memory.domain.repositories.context_repository import IContextRepository
from app.memory.domain.types.context_payload_types import ContextMetadataPayload
from app.retrieval.application.chunker import chunk_markdown
from app.retrieval.application.context_pack import build_context_pack
from app.retrieval.application.context_ranking import merge_hybrid_matches
from app.retrieval.application.embedding_provider import (
    EmbeddingProvider,
)
from app.retrieval.application.rag_health import build_rag_dependency_health
from app.retrieval.application.vector_serialization import vector_to_sqlite_json
from app.shared.exceptions import NotFoundError, ValidationError
from app.shared.types.types_convert_utils import enum_value, now_utc


class ContextService:
    """Use cases for Context Vault linting, storage, and retrieval."""

    def __init__(
        self,
        repository: IContextRepository,
        embedding_provider: EmbeddingProvider | None = None,
        vector_retrieval_enabled: bool = False,
    ) -> None:
        """Initialize service dependencies.

        Args:
            repository: Context persistence port.
            embedding_provider: Optional local embedding provider.
            vector_retrieval_enabled: Whether vector indexing and query paths are wired.

        Returns:
            None.
        """
        self._repository = repository
        self._embedding_provider = embedding_provider
        self._vector_retrieval_enabled = vector_retrieval_enabled

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

    async def save(
        self,
        kind: ContextKind,
        title: str,
        content: str,
        summary: str | None = None,
        project: str | None = None,
        scope: ContextScope = ContextScope.PROJECT,
        workspace_id: str | None = None,
        agent_id: str | None = None,
        user_id: str | None = None,
        session_id: str | None = None,
        visibility: ContextScope = ContextScope.PROJECT,
        source_agent: str = "Hermes",
        source_type: ContextSourceType = ContextSourceType.AGENT,
        importance: ContextImportance = ContextImportance.MEDIUM,
        tags: list[str] | None = None,
        expires_at: datetime | None = None,
        context_metadata: ContextMetadataPayload | None = None,
    ) -> ContextRecord:
        """Lint, redact, chunk, and persist a context.

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
            source_type: Source category.
            importance: Recall priority.
            tags: Caller-provided tags.
            expires_at: Optional expiration timestamp.
            context_metadata: Optional metadata payload.

        Returns:
            Stored context read model.
        """
        kind = enum_value(kind, ContextKind, "kind")
        scope = enum_value(scope, ContextScope, "scope")
        visibility = enum_value(visibility, ContextScope, "visibility")
        source_type = enum_value(source_type, ContextSourceType, "source_type")
        importance = enum_value(importance, ContextImportance, "importance")
        if tags is None:
            lint_tags: list[str] = []
        else:
            lint_tags = tags
        lint_result = self.lint(
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
            tags=lint_tags,
        )
        if lint_result.status is ContextStorageStatus.BLOCKED_SECRET_RISK:
            raise ValidationError("Context blocked by high-risk secret policy")

        now = now_utc()
        normalized_summary = lint_result.normalized["summary"]
        if normalized_summary == "":
            normalized_summary = title
        markdown_chunks = list(
            chunk_markdown(title=title, content=lint_result.redacted_content)
        )
        embedding_fields = self._chunk_embedding_fields(
            [chunk.content for chunk in markdown_chunks]
        )
        chunks = [
            ContextChunkCreate(
                chunk_index=chunk.chunk_index,
                heading=chunk.heading,
                content=chunk.content,
                token_count=chunk.token_count,
                content_hash=chunk.content_hash,
                chunk_metadata=chunk.metadata,
                embedding=embedding,
                embedding_model=embedding_model,
                embedding_dimensions=embedding_dimensions,
                created_at=now,
            )
            for chunk, (
                embedding,
                embedding_model,
                embedding_dimensions,
            ) in zip(markdown_chunks, embedding_fields, strict=True)
        ]
        safe_tags = lint_result.normalized["tags"]

        context = await self._repository.create(
            payload=ContextCreate(
                kind=kind,
                title=title.strip(),
                summary=normalized_summary,
                content=lint_result.redacted_content,
                content_format=ContextContentFormat.MARKDOWN,
                project=project,
                scope=scope,
                workspace_id=workspace_id,
                agent_id=agent_id,
                user_id=user_id,
                session_id=session_id,
                visibility=visibility,
                source_agent=source_agent,
                source_type=source_type,
                importance=importance,
                tags=safe_tags,
                status=lint_result.status,
                quality_score=lint_result.score,
                warnings=lint_result.warnings,
                restore_prompt=_extract_restore_prompt(lint_result.redacted_content),
                context_metadata=_metadata_or_empty(context_metadata),
                created_at=now,
                updated_at=now,
                expires_at=expires_at,
            ),
            chunks=chunks,
        )
        return context

    async def prepare_compact(
        self,
        current_goal: str,
        completed: list[str],
        in_progress: list[str],
        key_decisions: list[str],
        next_actions: list[str],
        risks: list[str],
        project: str | None = None,
        scope: ContextScope = ContextScope.PROJECT,
        workspace_id: str | None = None,
        agent_id: str | None = None,
        user_id: str | None = None,
        session_id: str | None = None,
        visibility: ContextScope = ContextScope.PROJECT,
        source_agent: str = "Hermes",
    ) -> ContextRecord:
        """Build and save a compact handoff context from structured state.

        Args:
            current_goal: Current work goal.
            completed: Completed work bullets.
            in_progress: Active work bullets.
            key_decisions: Decision bullets.
            next_actions: Next action bullets.
            risks: Risk/watchout bullets.
            project: Optional project scope.
            scope: Recall-routing scope.
            workspace_id: Optional workspace identifier.
            agent_id: Optional agent identifier.
            user_id: Optional user identifier.
            session_id: Optional session identifier.
            visibility: Recall visibility scope.
            source_agent: Agent that produced the compact context.

        Returns:
            Stored compact context read model.
        """
        context = await self.save(
            kind=ContextKind.COMPACT,
            title=f"Compact: {current_goal}",
            summary="Compact handoff prepared for Alexandria-Hermes.",
            content=build_compact_context_content(
                current_goal=current_goal,
                completed=completed,
                in_progress=in_progress,
                key_decisions=key_decisions,
                next_actions=next_actions,
                risks=risks,
            ),
            project=project,
            scope=scope,
            workspace_id=workspace_id,
            agent_id=agent_id,
            user_id=user_id,
            session_id=session_id,
            visibility=visibility,
            source_agent=source_agent,
            source_type=ContextSourceType.AGENT,
            importance=ContextImportance.HIGH,
            tags=["compact", "handoff"],
        )
        return context

    async def capture_harness(self, payload: HarnessCapture) -> ContextRecord:
        """Save an agent-owned execution harness as Context Vault memory.

        Args:
            payload: Harness capture command.

        Returns:
            Stored HARNESS context read model.
        """
        scope = enum_value(payload.scope, ContextScope, "scope")
        context = await self.save(
            kind=ContextKind.HARNESS,
            title=f"Harness: {payload.task_goal.strip()}",
            summary=payload.summary,
            content=build_harness_context_content(payload),
            project=payload.project,
            scope=scope,
            workspace_id=payload.workspace_id,
            agent_id=payload.agent_id,
            user_id=payload.user_id,
            session_id=payload.session_id,
            visibility=scope,
            source_agent=payload.source_agent,
            source_type=ContextSourceType.AGENT,
            importance=ContextImportance.HIGH,
            tags=["harness", *_clean_harness_tags(payload.recall_keywords)],
            context_metadata=harness_context_metadata(payload),
        )
        return context

    async def get(self, context_id: str) -> ContextRecord:
        """Return one context or raise not-found.

        Args:
            context_id: Context identifier.

        Returns:
            Stored context read model.
        """
        context = await self._repository.get(context_id)
        if context is None:
            raise NotFoundError(f"Context not found: {context_id}")
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
            raise ValidationError("query is required")
        strategy = enum_value(strategy, RagStrategy, "strategy")
        if kind is not None:
            kind = enum_value(kind, ContextKind, "kind")
        if include_scopes is not None:
            include_scopes = [
                enum_value(scope, ContextScope, "include_scopes")
                for scope in include_scopes
            ]
        health = self.rag_health()
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
            matches = await self._repository.search_fts(
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
            matches = await self._search_vector(
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
            fts_matches = await self._repository.search_fts(
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
            vector_matches = await self._search_vector(
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

    async def reindex_embeddings(self, limit: int = 100) -> ContextReindexResult:
        """Backfill embeddings for stored context chunks.

        Args:
            limit: Maximum chunks to reindex in this batch.

        Returns:
            Context reindex result.
        """
        if limit < 1:
            raise ValidationError("limit must be at least 1")
        provider = self._embedding_provider
        health = self.rag_health()
        warnings = list(health.warnings)
        if (
            provider is None
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

        chunks = await self._repository.chunks_missing_embeddings(
            model_name=provider.model_name,
            dimensions=provider.dimensions,
            limit=limit,
        )
        embeddings = provider.embed_documents([chunk.content for chunk in chunks])
        if len(embeddings) != len(chunks):
            raise ValidationError(
                "Embedding provider returned an unexpected vector count"
            )

        updates: list[ContextChunkEmbeddingUpdate] = []
        for chunk, embedding in zip(chunks, embeddings, strict=True):
            if len(embedding) != provider.dimensions:
                raise ValidationError(
                    "Embedding provider returned an unexpected dimension"
                )
            try:
                serialized = vector_to_sqlite_json(embedding)
            except ValueError as exc:
                raise ValidationError(str(exc)) from exc
            updates.append(
                ContextChunkEmbeddingUpdate(
                    chunk_id=chunk.id,
                    embedding=serialized,
                    embedding_model=provider.model_name,
                    embedding_dimensions=provider.dimensions,
                )
            )
        updated = await self._repository.update_chunk_embeddings(updates)
        result = ContextReindexResult(
            scanned=len(chunks),
            updated=updated,
            skipped=len(chunks) - updated,
            warnings=warnings,
        )
        return result

    def _chunk_embedding_fields(
        self,
        chunk_contents: list[str],
    ) -> list[tuple[str | None, str | None, int | None]]:
        if not self._vector_retrieval_enabled or self._embedding_provider is None:
            return [(None, None, None) for _ in chunk_contents]

        provider = self._embedding_provider
        embeddings = provider.embed_documents(chunk_contents)
        if len(embeddings) != len(chunk_contents):
            raise ValidationError(
                "Embedding provider returned an unexpected vector count"
            )

        fields: list[tuple[str | None, str | None, int | None]] = []
        for embedding in embeddings:
            if len(embedding) != provider.dimensions:
                raise ValidationError(
                    "Embedding provider returned an unexpected dimension"
                )
            try:
                serialized = vector_to_sqlite_json(embedding)
            except ValueError as exc:
                raise ValidationError(str(exc)) from exc
            fields.append((serialized, provider.model_name, provider.dimensions))
        return fields

    async def _search_vector(
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
        query_embedding = provider.embed_query(query)
        if len(query_embedding) != provider.dimensions:
            raise ValidationError("Embedding provider returned an unexpected dimension")
        matches = await self._repository.search_vector(
            query_embedding=query_embedding,
            model_name=provider.model_name,
            dimensions=provider.dimensions,
            limit=limit,
            project=project,
            kind=kind,
            include_scopes=include_scopes,
            workspace_id=workspace_id,
            agent_id=agent_id,
            user_id=user_id,
            session_id=session_id,
        )
        return matches


def _extract_restore_prompt(content: str) -> str | None:
    marker = "## Restore Prompt"
    if marker not in content:
        return None
    tail = content.split(marker, maxsplit=1)[1].strip()
    if not tail:
        return None
    next_heading = tail.find("\n## ")
    return tail if next_heading == -1 else tail[:next_heading].strip()


def _metadata_or_empty(
    metadata: ContextMetadataPayload | None,
) -> ContextMetadataPayload:
    if metadata is None:
        empty_metadata: ContextMetadataPayload = {}
        return empty_metadata
    return metadata


def _clean_harness_tags(values: list[str]) -> list[str]:
    return sorted({value.strip() for value in values if value.strip()})
