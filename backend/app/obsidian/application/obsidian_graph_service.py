"""Application service for Obsidian graph related-note reads."""

from __future__ import annotations

from app.obsidian.application.obsidian_service import ObsidianService
from app.obsidian.domain.entities.obsidian_note import ObsidianRelatedNote
from app.obsidian.domain.repositories.obsidian_repository import (
    IObsidianIndexRepository,
)
from app.obsidian.infrastructure.markdown.paths import safe_relative_path
from app.shared.exceptions import ObsidianNotFoundError


class ObsidianGraphService:
    """Read graph relationships from the rebuildable Obsidian edge index."""

    def __init__(
        self,
        *,
        repository: IObsidianIndexRepository,
        obsidian_service: ObsidianService,
    ) -> None:
        self._repository = repository
        self._obsidian_service = obsidian_service

    async def related_notes_by_path(
        self,
        relative_path: str,
        *,
        limit: int = 10,
        refresh: bool = True,
    ) -> list[ObsidianRelatedNote]:
        """Return graph-related notes for one vault-relative path.

        Args:
            relative_path: Vault-relative Markdown path.
            limit: Maximum related-note count.
            refresh: Whether to reindex before reading edges.

        Returns:
            Ranked graph-related notes.
        """
        if refresh:
            await self._obsidian_service.reindex()
        safe_path = str(safe_relative_path(relative_path))
        note = await self._repository.get_by_path(safe_path)
        if note is None:
            raise ObsidianNotFoundError(f"Obsidian note not found: {safe_path}")
        return await self._repository.related_notes(note_id=note.note_id, limit=limit)

    async def related_notes(
        self,
        note_id: str,
        *,
        limit: int = 10,
        refresh: bool = True,
    ) -> list[ObsidianRelatedNote]:
        """Return graph-related notes for one stable note id.

        Args:
            note_id: Stable source/target note id.
            limit: Maximum related-note count.
            refresh: Whether to reindex before reading edges.

        Returns:
            Ranked graph-related notes.
        """
        if refresh:
            await self._obsidian_service.reindex()
        note = await self._repository.get_by_id(note_id)
        if note is None:
            raise ObsidianNotFoundError(f"Obsidian note not found: {note_id}")
        return await self._repository.related_notes(note_id=note_id, limit=limit)
