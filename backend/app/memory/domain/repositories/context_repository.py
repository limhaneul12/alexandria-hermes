"""Context Vault repository abstraction."""

from __future__ import annotations

from abc import ABC, abstractmethod

from app.memory.domain.contracts.context_contracts import (
    ContextChunkCreate,
    ContextCreate,
)
from app.memory.domain.entities.context_read_models import (
    ContextChunkRecord,
    ContextRecord,
    ContextSearchMatch,
)
from app.memory.domain.event_enum.context_enums import ContextKind, ContextScope


class IContextRepository(ABC):
    """Persistence contract for Context Vault operations."""

    @abstractmethod
    async def create(
        self,
        *,
        payload: ContextCreate,
        chunks: list[ContextChunkCreate],
    ) -> ContextRecord:
        """Persist a context with its chunks.

        Args:
            payload: Context fields to persist.
            chunks: Search chunks derived from the context content.

        Returns:
            Stored context read model.
        """

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
    async def record_access(self, context_id: str) -> ContextRecord:
        """Record an access event for recall/audit purposes.

        Args:
            context_id: Context identifier.

        Returns:
            Updated context read model.
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
