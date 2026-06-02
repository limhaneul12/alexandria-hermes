"""Search-source port for Context RAG retrieval."""

from __future__ import annotations

from abc import ABC, abstractmethod

from app.memory.domain.contracts.context_contracts import (
    ContextChunkEmbeddingUpdate,
)
from app.memory.domain.entities.context_read_models import (
    ContextChunkRecord,
    ContextSearchMatch,
)
from app.memory.domain.event_enum.context_enums import (
    ContextKind,
    ContextScope,
    RagHealthState,
)


class IContextSearchSource(ABC):
    """Persistence-backed source that can contribute Context RAG matches."""

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
        """Search source chunks with SQLite FTS5.

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
            Ranked source matches mapped into Context RAG read models.
        """

    @abstractmethod
    async def search_vector(
        self,
        *,
        query_embedding: list[float],
        model_name: str,
        dimensions: int,
        fingerprint_key: str,
        limit: int,
        project: str | None = None,
        kind: ContextKind | None = None,
        include_scopes: list[ContextScope] | None = None,
        workspace_id: str | None = None,
        agent_id: str | None = None,
        user_id: str | None = None,
        session_id: str | None = None,
    ) -> list[ContextSearchMatch]:
        """Search source chunks with stored embeddings.

        Args:
            query_embedding: Query embedding vector.
            model_name: Embedding model that produced the query vector.
            dimensions: Expected embedding dimensions.
            fingerprint_key: Current embedding generation fingerprint key.
            limit: Maximum returned matches.
            project: Optional project filter.
            kind: Optional context kind filter.
            include_scopes: Optional recall scope filter.
            workspace_id: Optional workspace filter.
            agent_id: Optional agent filter.
            user_id: Optional user filter.
            session_id: Optional session filter.

        Returns:
            Ranked source matches mapped into Context RAG read models.
        """

    @abstractmethod
    async def chunks_missing_embeddings(
        self,
        *,
        model_name: str,
        dimensions: int,
        fingerprint_key: str,
        limit: int,
        force: bool = False,
    ) -> list[ContextChunkRecord]:
        """Return source chunks that need embedding backfill or rebuild.

        Args:
            model_name: Current embedding model name.
            dimensions: Current embedding dimensions.
            fingerprint_key: Current embedding generation fingerprint key.
            limit: Maximum chunks to scan.
            force: Whether to rebuild existing embeddings even if metadata matches.

        Returns:
            Chunks missing current embedding metadata or selected for rebuild.
        """

    @abstractmethod
    async def embedding_index_status(
        self,
        *,
        model_name: str,
        dimensions: int,
        fingerprint_key: str,
    ) -> RagHealthState:
        """Return whether the source embedding index matches the current provider.

        Args:
            model_name: Current embedding model name.
            dimensions: Current embedding dimensions.
            fingerprint_key: Current embedding generation fingerprint key.

        Returns:
            HEALTHY when indexed embeddings match; REINDEX_REQUIRED otherwise.
        """

    @abstractmethod
    async def update_chunk_embeddings(
        self,
        updates: list[ContextChunkEmbeddingUpdate],
    ) -> int:
        """Persist source chunk embedding updates.

        Args:
            updates: Embedding updates keyed by source-specific chunk identifier.

        Returns:
            Number of chunks updated.
        """
