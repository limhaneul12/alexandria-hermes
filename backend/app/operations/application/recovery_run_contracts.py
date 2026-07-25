"""Service protocols required by operational recovery execution."""

from __future__ import annotations

from typing import Protocol

from app.memory.domain.entities.context_read_models import ContextReindexResult
from app.obsidian.domain.contracts.obsidian_contracts import ObsidianSearchQuery
from app.obsidian.domain.entities.obsidian_note import (
    ObsidianNote,
    ObsidianReindexResult,
    ObsidianSearchHit,
)
from app.operations.application.operational_readiness_service import (
    ContextReadinessService,
    ObsidianReadinessService,
)


class ContextRecoveryService(ContextReadinessService, Protocol):
    """Context service subset used by recovery execution."""

    async def reindex_embeddings(
        self,
        limit: int = 100,
        *,
        force: bool = False,
    ) -> ContextReindexResult:
        """Rebuild retrieval embeddings.

        Args:
            limit: Maximum chunks to rebuild.
            force: Whether to rebuild existing embeddings.

        Returns:
            Context embedding reindex result.
        """


class ObsidianRecoveryService(ObsidianReadinessService, Protocol):
    """Obsidian service subset used by recovery execution."""

    async def reindex(self) -> ObsidianReindexResult:
        """Rebuild the Obsidian vault index.

        Returns:
            Obsidian reindex result.
        """

    async def search(
        self,
        query: ObsidianSearchQuery,
        *,
        refresh: bool = True,
    ) -> list[ObsidianSearchHit]:
        """Search indexed Obsidian notes.

        Args:
            query: Search query.
            refresh: Whether to refresh before searching.

        Returns:
            Matching Obsidian notes.
        """

    async def read_note(self, note_id: str) -> ObsidianNote:
        """Read one indexed Obsidian note by stable id.

        Args:
            note_id: Expected note identifier.

        Returns:
            Indexed Obsidian note.
        """

    async def read_note_by_path(self, relative_path: str) -> ObsidianNote:
        """Read one indexed Obsidian note by vault-relative path.

        Args:
            relative_path: Vault-relative note path.

        Returns:
            Indexed Obsidian note.
        """
