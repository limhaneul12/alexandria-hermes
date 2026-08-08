"""Read persistence port for the rebuildable Obsidian note index."""

from __future__ import annotations

from abc import ABC, abstractmethod

from app.obsidian.domain.contracts.obsidian_contracts import (
    ObsidianContextDuplicateQuery,
    ObsidianSearchQuery,
)
from app.obsidian.domain.entities.obsidian_note import (
    ObsidianNote,
    ObsidianSearchHit,
)


class IObsidianIndexQueryRepository(ABC):
    """Read and search the rebuildable PostgreSQL Obsidian index."""

    @abstractmethod
    async def get_by_id(self, note_id: str) -> ObsidianNote | None:
        """Read one indexed note by stable id.

        Args:
            note_id: Stable note id.

        Returns:
            Note entity when found.
        """

    @abstractmethod
    async def get_by_path(self, relative_path: str) -> ObsidianNote | None:
        """Read one indexed note by vault-relative path.

        Args:
            relative_path: Vault-relative path.

        Returns:
            Note entity when found.
        """

    @abstractmethod
    async def find_context_duplicate(
        self,
        query: ObsidianContextDuplicateQuery,
    ) -> ObsidianNote | None:
        """Return an indexed Context with the same identity and content hash.

        Args:
            query: Canonical duplicate lookup constraints.

        Returns:
            Existing duplicate Context when found.
        """

    @abstractmethod
    async def search(self, query: ObsidianSearchQuery) -> list[ObsidianSearchHit]:
        """Search indexed notes using the PostgreSQL FTS index.

        Args:
            query: Search filters and query text.

        Returns:
            Ranked search hits.
        """

    @abstractmethod
    async def count_by_status(self) -> tuple[int, int, int]:
        """Return indexed, stale, and error note counts.

        Returns:
            Tuple of indexed, stale, and error note counts.
        """
