"""Write persistence port for the rebuildable Obsidian note index."""

from __future__ import annotations

from abc import ABC, abstractmethod

from app.obsidian.domain.contracts.obsidian_contracts import ObsidianNoteIndex
from app.obsidian.domain.entities.obsidian_note import ObsidianNote


class IObsidianIndexWriteRepository(ABC):
    """Mutate rebuildable PostgreSQL note index state."""

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
    async def resolve_edge_targets(self) -> int:
        """Resolve edge target ids from indexed target paths.

        Returns:
            Number of edge rows updated with a target note id.
        """
