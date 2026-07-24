"""Canonical Context lifecycle mutations for Obsidian Markdown."""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path

from app.obsidian.application.notes.obsidian_note_indexer import note_index_from_path
from app.obsidian.domain.entities.obsidian_note import ObsidianIndexError, ObsidianNote
from app.obsidian.domain.event_enum.obsidian_enums import (
    AlexandriaNoteType,
    ObsidianIndexErrorCode,
)
from app.obsidian.domain.repositories.obsidian_repository import (
    IObsidianIndexRepository,
)
from app.obsidian.infrastructure.markdown.atomic_markdown_write import (
    atomic_write_markdown,
)
from app.obsidian.infrastructure.markdown.frontmatter import (
    update_frontmatter_scalars,
)
from app.obsidian.infrastructure.markdown.paths import resolve_note_path
from app.shared.exceptions import ObsidianIndexWriteError, ObsidianValidationError
from app.shared.types.types_convert_utils import now_utc


class ObsidianContextLifecycleCoordinator:
    """Patch Context lifecycle scalars while preserving canonical YAML."""

    def __init__(
        self,
        repository: IObsidianIndexRepository,
        vault_path: Path,
        alexandria_root: str,
    ) -> None:
        self._repository = repository
        self._vault_path = vault_path
        self._alexandria_root = alexandria_root

    async def archive(self, note: ObsidianNote) -> ObsidianNote:
        """Archive a canonical Context note.

        Args:
            note: Indexed canonical Context.

        Returns:
            Reindexed archived Context.
        """
        if note.alexandria_type is not AlexandriaNoteType.CONTEXT:
            raise ObsidianValidationError(f"Not a Context note: {note.note_id}")
        return await self.update_scalars(note, {"status": "archived"})

    async def mark_superseded(
        self,
        superseded_context_id: str,
        replacement_context_id: str,
    ) -> None:
        """Record one idempotent supersede backlink on canonical Markdown.

        Args:
            superseded_context_id: Prior canonical Context identifier.
            replacement_context_id: Replacement canonical Context identifier.
        """
        superseded = await self._repository.get_by_id(superseded_context_id)
        if superseded is None:
            raise ObsidianValidationError(
                "INVALID_SUPERSEDE: superseded Context disappeared during save"
            )
        existing_replacement = superseded.frontmatter.get("superseded_by_context_id")
        if existing_replacement not in (None, replacement_context_id):
            raise ObsidianValidationError(
                "INVALID_SUPERSEDE: Context already has a different replacement"
            )
        if (
            existing_replacement == replacement_context_id
            and superseded.status == "superseded"
        ):
            return
        version = superseded.frontmatter.get("version")
        next_version = version + 1 if isinstance(version, int) else 2
        await self.update_scalars(
            superseded,
            {
                "status": "superseded",
                "version": str(next_version),
                "superseded_by_context_id": replacement_context_id,
            },
        )

    async def update_scalars(
        self,
        note: ObsidianNote,
        replacements: Mapping[str, str],
    ) -> ObsidianNote:
        """Patch owned scalars without rewriting unrelated YAML.

        Args:
            note: Indexed canonical Context.
            replacements: Owned top-level scalar values to update.

        Returns:
            Reindexed updated Context.
        """
        absolute = resolve_note_path(self._vault_path, note.relative_path)
        scalar_updates = {**replacements, "updated_at": now_utc().isoformat()}
        updated_text = update_frontmatter_scalars(
            absolute.read_text(encoding="utf-8"),
            scalar_updates,
        )
        atomic_write_markdown(absolute, updated_text)
        payload = note_index_from_path(
            absolute,
            note.relative_path,
            alexandria_root=self._alexandria_root,
        )
        if payload is None:
            raise ObsidianValidationError("updated Context lost managed frontmatter")
        try:
            return await self._repository.upsert_note(payload)
        except ObsidianIndexWriteError as exc:
            await self._repository.record_index_error(
                ObsidianIndexError(
                    note_path=note.relative_path,
                    context_id=note.note_id,
                    error_code=ObsidianIndexErrorCode.INDEX_WRITE_FAILED,
                    error_message="Rebuildable index write failed",
                    detected_at=now_utc(),
                )
            )
            raise ObsidianValidationError(
                "INDEX_WRITE_FAILED: updated Markdown was preserved for reindex"
            ) from exc
