"""Application service for Context Vault storage and retrieval."""

from __future__ import annotations

from datetime import datetime

from app.library.application.context_compact import build_compact_context_content
from app.library.application.context_lint import (
    ContextLintInput,
    ContextLintResult,
    lint_context,
)
from app.library.application.retrieval.chunker import chunk_markdown
from app.library.application.retrieval.context_pack import build_context_pack
from app.library.application.retrieval.embedding_provider import (
    EmbeddingProvider,
)
from app.library.application.retrieval.rag_health import build_rag_dependency_health
from app.library.domain.contracts.context_contracts import (
    ContextChunkCreate,
    ContextCreate,
)
from app.library.domain.entities.context_read_models import (
    ContextChunkRecord,
    ContextPack,
    ContextRecord,
    RagDependencyHealth,
)
from app.library.domain.event_enum.context_enums import (
    ContextContentFormat,
    ContextImportance,
    ContextKind,
    ContextSourceType,
    ContextStorageStatus,
    RagHealthState,
    RagStrategy,
)
from app.library.domain.repositories.context_repository import IContextRepository
from app.library.domain.types.context_payload_types import ContextMetadataPayload
from app.shared.exceptions import NotFoundError, ValidationError
from app.shared.types.types_convert_utils import now_utc


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
        source_agent: str,
        tags: list[str],
    ) -> ContextLintResult:
        """Run Context Harness linting without persistence.

        Args:
            kind: Context entry kind.
            title: Human-readable title.
            content: Markdown content.
            summary: Optional summary supplied by the caller.
            project: Optional project scope.
            source_agent: Agent that produced the content.
            tags: Caller-provided tags.

        Returns:
            Context lint result with redaction and quality details.
        """
        result = lint_context(
            ContextLintInput(
                kind=kind,
                title=title,
                content=content,
                summary=summary,
                project=project,
                source_agent=source_agent,
                tags=tags,
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
            source_agent: Agent that produced the content.
            source_type: Source category.
            importance: Recall priority.
            tags: Caller-provided tags.
            expires_at: Optional expiration timestamp.
            context_metadata: Optional metadata payload.

        Returns:
            Stored context read model.
        """
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
            source_agent=source_agent,
            tags=lint_tags,
        )
        if lint_result.status is ContextStorageStatus.BLOCKED_SECRET_RISK:
            raise ValidationError("Context blocked by high-risk secret policy")

        now = now_utc()
        normalized_summary = lint_result.normalized["summary"]
        if normalized_summary == "":
            normalized_summary = title
        chunks = [
            ContextChunkCreate(
                chunk_index=chunk.chunk_index,
                heading=chunk.heading,
                content=chunk.content,
                token_count=chunk.token_count,
                content_hash=chunk.content_hash,
                chunk_metadata=chunk.metadata,
                created_at=now,
            )
            for chunk in chunk_markdown(
                title=title, content=lint_result.redacted_content
            )
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
            source_agent=source_agent,
            source_type=ContextSourceType.AGENT,
            importance=ContextImportance.HIGH,
            tags=["compact", "handoff"],
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
            source_agent: Optional source-agent filter.
            tag: Optional tag filter.
            include_archived: Whether archived entries are included.

        Returns:
            Matching context rows and total count before pagination.
        """
        result = await self._repository.list_all(
            limit=limit,
            offset=offset,
            kind=kind,
            project=project,
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

    async def access(self, context_id: str) -> ContextRecord:
        """Record an access event.

        Args:
            context_id: Context identifier.

        Returns:
            Updated context read model.
        """
        context = await self._repository.record_access(context_id)
        return context

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
    ) -> ContextPack:
        """Return a context pack for a query.

        Args:
            query: Search query text.
            strategy: Requested retrieval strategy.
            limit: Maximum matches.
            project: Optional project filter.
            kind: Optional context kind filter.

        Returns:
            Context pack containing retrieved matches and warnings.
        """
        if not query.strip():
            raise ValidationError("query is required")
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
        matches = await self._repository.search_fts(
            query=query,
            limit=limit,
            project=project,
            kind=kind,
        )
        context_pack = ContextPack(
            query=query,
            strategy=strategy,
            effective_strategy=effective,
            warnings=warnings,
            matches=matches,
            context_pack=build_context_pack(query=query, matches=matches),
        )
        return context_pack


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
