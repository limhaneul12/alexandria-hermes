"""Read port for rows used to rebuild an Obsidian graph projection."""

from __future__ import annotations

from abc import ABC, abstractmethod

from app.obsidian.domain.entities.obsidian_note import ObsidianEdge, ObsidianNote


class IObsidianGraphProjectionSourceRepository(ABC):
    """Read typed note and edge rows from the rebuildable Obsidian index."""

    @abstractmethod
    async def list_projection_notes(self) -> tuple[ObsidianNote, ...]:
        """Return all indexed-note rows considered by projection building.

        Returns:
            Typed note rows from the rebuildable index.
        """

    @abstractmethod
    async def list_projection_edges(self) -> tuple[ObsidianEdge, ...]:
        """Return all cached graph-edge rows considered by projection building.

        Returns:
            Typed edge rows derived from canonical Markdown.
        """
