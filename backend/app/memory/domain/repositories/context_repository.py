"""Context Vault repository abstraction."""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime

from app.memory.domain.contracts.context_contracts import (
    ContextAccessCreate,
    ContextChunkEmbeddingUpdate,
)
from app.memory.domain.entities.context_read_models import (
    ContextAccessEventRecord,
    ContextChunkRecord,
    ContextRecord,
    ContextSearchMatch,
)
from app.memory.domain.event_enum.context_enums import ContextKind, ContextScope
from app.memory.domain.repositories.context_search_source import IContextSearchSource


class IContextRepository(IContextSearchSource, ABC):
    """Persistence contract for Context Vault operations."""

    @abstractmethod
    async def get(self, context_id: str) -> ContextRecord | None:
        """Return one non-deleted context by id.

        Args:
            context_id: Context identifier.

        Returns:
            Stored context read model when found.
        """

    @abstractmethod
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
        """List contexts with filters and total count.

        Args:
            limit: Maximum returned entries.
            offset: Pagination offset.
            kind: Optional context kind filter.
            project: Optional project filter.
            scope: Optional context scope filter.
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

    @abstractmethod
    async def chunks(self, context_id: str) -> list[ContextChunkRecord]:
        """Return chunks for one context.

        Args:
            context_id: Context identifier.

        Returns:
            Stored chunks for the context.
        """

    @abstractmethod
    async def archive(self, context_id: str) -> ContextRecord:
        """Archive one context instead of deleting it.

        Args:
            context_id: Context identifier.

        Returns:
            Archived context read model.
        """

    @abstractmethod
    async def delete(self, context_id: str) -> None:
        """Hard delete one context and dependent rows.

        Args:
            context_id: Context identifier.

        Returns:
            None.
        """

    @abstractmethod
    async def record_access(self, payload: ContextAccessCreate) -> ContextRecord:
        """Record an access event for recall/audit purposes.

        Args:
            payload: Context access event fields.

        Returns:
            Updated context read model.
        """

    @abstractmethod
    async def access_events(
        self, *, context_id: str, limit: int = 5
    ) -> list[ContextAccessEventRecord]:
        """List recent access events for one context.

        Args:
            context_id: Context identifier.
            limit: Maximum events to return.

        Returns:
            Recent access events ordered newest first.
        """

    @abstractmethod
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
        """Search context chunks with SQLite FTS5.

        Args:
            query: Search query text.
            limit: Maximum returned matches.
            project: Optional project filter.
            kind: Optional context kind filter.
            include_scopes: Optional recall scope filter.
            workspace_id: Optional workspace filter.
            agent_id: Optional agent filter.
            user_id: Optional user filter.
            session_id: Optional session filter.

        Returns:
            Ranked context matches.
        """

    @abstractmethod
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
        """Search context chunks with stored embeddings.

        Args:
            query_embedding: Query embedding vector.
            model_name: Embedding model that produced the query vector.
            dimensions: Expected embedding dimensions.
            limit: Maximum returned matches.
            project: Optional project filter.
            kind: Optional context kind filter.
            include_scopes: Optional recall scope filter.
            workspace_id: Optional workspace filter.
            agent_id: Optional agent filter.
            user_id: Optional user filter.
            session_id: Optional session filter.

        Returns:
            Ranked vector matches.
        """

    @abstractmethod
    async def chunks_missing_embeddings(
        self,
        *,
        model_name: str,
        dimensions: int,
        limit: int,
        force: bool = False,
    ) -> list[ContextChunkRecord]:
        """Return chunks that need embedding backfill or forced rebuild.

        Args:
            model_name: Current embedding model name.
            dimensions: Current embedding dimensions.
            limit: Maximum chunks to scan.
            force: Whether to rebuild existing embeddings even if model metadata matches.

        Returns:
            Chunks missing current embedding metadata or selected for forced rebuild.
        """

    @abstractmethod
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
