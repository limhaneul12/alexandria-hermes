"""Repository port for Obsidian note index storage."""

from __future__ import annotations

from abc import ABC, abstractmethod

from app.obsidian.domain.contracts.obsidian_contracts import (
    ObsidianNoteIndex,
    ObsidianSearchQuery,
)
from app.obsidian.domain.entities.obsidian_note import (
    ObsidianNote,
    ObsidianSearchHit,
)


class IObsidianIndexRepository(ABC):
    """Persistence contract for the rebuildable Obsidian SQLite index."""

    @abstractmethod
    async def ensure_search_tables(self) -> None:
        """Create search support tables that are not represented by ORM metadata."""

    @abstractmethod
    async def upsert_note(self, payload: ObsidianNoteIndex) -> ObsidianNote:
        """Create or update one indexed note and its chunks.

        Args:
            payload: Indexed note payload.

        Returns:
            Persisted note entity.
        """

    @abstractmethod
    async def mark_missing_stale(self, relative_paths: set[str]) -> int:
        """Mark indexed notes not present in the current scan as stale.

        Args:
            relative_paths: Paths observed during the current scan.

        Returns:
            Number of notes marked stale.
        """

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
    async def search(self, query: ObsidianSearchQuery) -> list[ObsidianSearchHit]:
        """Search indexed notes using the SQLite FTS cache.

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
