"""Obsidian-backed Memory Compact repository implementation."""

from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path

from app.memory.domain.entities.memory_compact import (
    MemoryCompact,
    MemoryCompactSourceRef,
)
from app.memory.domain.event_enum.memory_compact_enums import (
    MemoryCompactReviewVerdict,
    MemoryCompactStatus,
)
from app.memory.domain.repositories.memory_compact_repository import (
    IMemoryCompactRepository,
    MemoryCompactCreate,
)
from app.memory.infrastructure.repositories.memory_compacts.obsidian_markdown import (
    NOTE_SUFFIX,
    is_safe_note_id,
    read_compact_file,
    resolve_base_dir,
    serialize_compact,
)
from app.shared.exceptions import MemoryCompactNotFoundError
from app.shared.infrastructure.identifiers import new_uuid
from app.shared.types.types_convert_utils import aware_utc_datetime


class ObsidianMemoryCompactRepository(IMemoryCompactRepository):
    """Persist Memory Compact artifacts as Markdown notes in an Obsidian vault."""

    def __init__(self, *, vault_path: str | Path, relative_dir: str | Path) -> None:
        """Initialize repository.

        Args:
            vault_path: Obsidian vault root path.
            relative_dir: Relative folder for Memory Compact notes.
        """
        self._base_dir = resolve_base_dir(vault_path, relative_dir)

    async def create(self, payload: MemoryCompactCreate) -> MemoryCompact:
        """Create one Memory Compact note and source-reference frontmatter.

        Args:
            payload: Memory Compact creation contract.

        Returns:
            Created Memory Compact entity.
        """
        now = datetime.now(UTC)
        compact_id = new_uuid()
        compact = MemoryCompact(
            id=compact_id,
            project=payload.project,
            covered_from=aware_utc_datetime(payload.covered_from),
            covered_to=aware_utc_datetime(payload.covered_to),
            markdown_body=payload.markdown_body,
            status=payload.status,
            source_refs=_source_refs(compact_id, payload),
            created_at=now,
            updated_at=now,
            archived_at=None,
            review_verdict=payload.review_verdict,
            review_score=payload.review_score,
            review_max_score=payload.review_max_score,
            reviewed_at=payload.reviewed_at,
        )
        if payload.status is MemoryCompactStatus.CURRENT:
            await self._supersede_current_project(payload.project, excluded_id=None)
        self._write_compact(compact)
        return compact

    async def get(self, compact_id: str) -> MemoryCompact | None:
        """Read one compact by id.

        Args:
            compact_id: Memory Compact identifier.

        Returns:
            Matching compact, or None when absent.
        """
        for compact in self._read_all_compacts():
            if compact.id == compact_id:
                return compact
        return None

    async def list_compacts(
        self,
        *,
        project: str | None = None,
        status: MemoryCompactStatus | None = None,
        covered_after: datetime | None = None,
        covered_before: datetime | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[MemoryCompact], int]:
        """List compacts and total count.

        Args:
            project: Project filter.
            status: Lifecycle status filter.
            covered_after: Coverage-overlap lower bound.
            covered_before: Coverage-overlap upper bound.
            limit: Maximum number of rows to return.
            offset: Number of rows to skip.

        Returns:
            Page of compacts and total matching count.
        """
        compacts = self._filter_compacts(
            project=project,
            status=status,
            covered_after=covered_after,
            covered_before=covered_before,
        )
        compacts.sort(key=lambda item: item.covered_to, reverse=True)
        total = len(compacts)
        return compacts[offset : offset + limit], total

    async def current(self, *, project: str | None = None) -> MemoryCompact | None:
        """Read current compact for a project.

        Args:
            project: Optional project filter; None addresses the default project.

        Returns:
            Current compact, or None when absent.
        """
        compacts = [
            item
            for item in self._read_all_compacts()
            if item.status is MemoryCompactStatus.CURRENT and item.project == project
        ]
        compacts.sort(key=lambda item: item.updated_at, reverse=True)
        return compacts[0] if compacts else None

    async def mark_current(
        self,
        compact_id: str,
        *,
        review_verdict: MemoryCompactReviewVerdict | None = None,
        review_score: int | None = None,
        review_max_score: int | None = None,
        reviewed_at: datetime | None = None,
    ) -> MemoryCompact:
        """Mark one compact current and supersede prior current for project.

        Args:
            compact_id: Memory Compact identifier.
            review_verdict: Latest librarian review verdict for the promotion.
            review_score: Latest librarian review total score.
            review_max_score: Latest librarian review maximum score.
            reviewed_at: Review timestamp.

        Returns:
            Updated current compact.
        """
        compact = await self.get(compact_id)
        if compact is None:
            raise MemoryCompactNotFoundError(f"Memory compact not found: {compact_id}")
        await self._supersede_current_project(compact.project, excluded_id=compact.id)
        updated = replace(
            compact,
            status=MemoryCompactStatus.CURRENT,
            updated_at=datetime.now(UTC),
            archived_at=None,
            review_verdict=review_verdict,
            review_score=review_score,
            review_max_score=review_max_score,
            reviewed_at=reviewed_at,
        )
        self._write_compact(updated)
        return updated

    async def archive(self, compact_id: str) -> MemoryCompact:
        """Archive one compact.

        Args:
            compact_id: Memory Compact identifier.

        Returns:
            Archived compact.
        """
        compact = await self.get(compact_id)
        if compact is None:
            raise MemoryCompactNotFoundError(f"Memory compact not found: {compact_id}")
        now = datetime.now(UTC)
        updated = replace(
            compact,
            status=MemoryCompactStatus.ARCHIVED,
            updated_at=now,
            archived_at=now,
        )
        self._write_compact(updated)
        return updated

    async def delete(self, compact_id: str) -> None:
        """Hard delete one compact note.

        Args:
            compact_id: Memory Compact identifier.

        Returns:
            None.
        """
        compact = await self.get(compact_id)
        if compact is None:
            raise MemoryCompactNotFoundError(f"Memory compact not found: {compact_id}")
        path = self._compact_path(compact.id)
        if path is not None and path.exists():
            path.unlink()
            return
        self._delete_scanned_note(compact.id)

    async def _supersede_current_project(
        self,
        project: str | None,
        excluded_id: str | None,
    ) -> None:
        now = datetime.now(UTC)
        for compact in self._read_all_compacts():
            if (
                compact.status is MemoryCompactStatus.CURRENT
                and compact.project == project
                and compact.id != excluded_id
            ):
                self._write_compact(
                    replace(
                        compact,
                        status=MemoryCompactStatus.SUPERSEDED,
                        updated_at=now,
                    )
                )

    def _filter_compacts(
        self,
        *,
        project: str | None,
        status: MemoryCompactStatus | None,
        covered_after: datetime | None,
        covered_before: datetime | None,
    ) -> list[MemoryCompact]:
        compacts = self._read_all_compacts()
        if project is not None:
            compacts = [item for item in compacts if item.project == project]
        if status is not None:
            compacts = [item for item in compacts if item.status is status]
        if covered_after is not None:
            lower_bound = aware_utc_datetime(covered_after)
            compacts = [item for item in compacts if item.covered_to >= lower_bound]
        if covered_before is not None:
            upper_bound = aware_utc_datetime(covered_before)
            compacts = [item for item in compacts if item.covered_from <= upper_bound]
        return compacts

    def _read_all_compacts(self) -> list[MemoryCompact]:
        compacts_by_id: dict[str, MemoryCompact] = {}
        for path in self._note_paths():
            compact = read_compact_file(path)
            if compact is not None:
                existing = compacts_by_id.get(compact.id)
                if existing is None or _compact_sort_key(compact) > _compact_sort_key(
                    existing
                ):
                    compacts_by_id[compact.id] = compact
        return list(compacts_by_id.values())

    def _delete_scanned_note(self, compact_id: str) -> None:
        for candidate in self._note_paths():
            compact = read_compact_file(candidate)
            if compact is not None and compact.id == compact_id:
                candidate.unlink()
                return

    def _note_paths(self) -> list[Path]:
        if not self._base_dir.exists():
            return []
        return sorted(self._base_dir.glob(f"*{NOTE_SUFFIX}"))

    def _compact_path(self, compact_id: str) -> Path | None:
        if not is_safe_note_id(compact_id):
            return None
        return self._base_dir / f"{compact_id}{NOTE_SUFFIX}"

    def _write_compact(self, compact: MemoryCompact) -> None:
        self._base_dir.mkdir(parents=True, exist_ok=True)
        path = self._compact_path(compact.id)
        if path is None:
            raise ValueError("Memory Compact id cannot be used as a note filename")
        temp_path = path.with_suffix(f"{NOTE_SUFFIX}.tmp")
        temp_path.write_text(serialize_compact(compact), encoding="utf-8")
        temp_path.replace(path)


def _source_refs(
    compact_id: str, payload: MemoryCompactCreate
) -> tuple[MemoryCompactSourceRef, ...]:
    return tuple(
        MemoryCompactSourceRef(
            id=new_uuid(),
            compact_id=compact_id,
            source_type=source_ref.source_type,
            source_id=source_ref.source_id,
            title=source_ref.title,
            detail_path=source_ref.detail_path,
            source_hash=source_ref.source_hash,
        )
        for source_ref in payload.source_refs
    )


def _compact_sort_key(compact: MemoryCompact) -> tuple[datetime, datetime]:
    return compact.updated_at, compact.created_at
