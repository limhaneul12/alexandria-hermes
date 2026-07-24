"""Repository port for Obsidian note index storage."""

from __future__ import annotations

from abc import ABC, abstractmethod

from app.obsidian.domain.contracts.obsidian_contracts import (
    ObsidianContextDuplicateQuery,
    ObsidianNoteIndex,
    ObsidianSearchQuery,
)
from app.obsidian.domain.entities.obsidian_note import (
    ObsidianIndexError,
    ObsidianLibrarianWorkflow,
    ObsidianNote,
    ObsidianRelatedNote,
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
    async def resolve_edge_targets(self) -> int:
        """Resolve edge target ids from indexed target paths.

        Returns:
            Number of edge rows updated with a target note id.
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
        """Search indexed notes using the SQLite FTS cache.

        Args:
            query: Search filters and query text.

        Returns:
            Ranked search hits.
        """

    @abstractmethod
    async def related_notes(
        self,
        *,
        note_id: str,
        limit: int,
    ) -> list[ObsidianRelatedNote]:
        """Return graph-related notes for one indexed note.

        Args:
            note_id: Source or target note id to expand.
            limit: Maximum related notes.

        Returns:
            Ranked related-note results.
        """

    @abstractmethod
    async def count_by_status(self) -> tuple[int, int, int]:
        """Return indexed, stale, and error note counts.

        Returns:
            Tuple of indexed, stale, and error note counts.
        """

    @abstractmethod
    async def record_index_error(self, error: ObsidianIndexError) -> None:
        """Persist one structured reindex error in the rebuildable index.

        Args:
            error: Structured note indexing failure.
        """

    @abstractmethod
    async def list_index_errors(self, limit: int = 20) -> list[ObsidianIndexError]:
        """Return recent structured reindex errors.

        Args:
            limit: Maximum number of recent errors to return.

        Returns:
            Recent structured indexing failures.
        """


class IObsidianWorkflowRepository(ABC):
    """Persistence contract for librarian workflow checkpoints."""

    @abstractmethod
    async def upsert_workflow(self, workflow: ObsidianLibrarianWorkflow) -> None:
        """Persist one workflow checkpoint.

        Args:
            workflow: Workflow checkpoint entity.
        """

    @abstractmethod
    async def get_workflow(self, thread_id: str) -> ObsidianLibrarianWorkflow | None:
        """Read one workflow checkpoint by thread id.

        Args:
            thread_id: Workflow thread id.

        Returns:
            Workflow when found.
        """
