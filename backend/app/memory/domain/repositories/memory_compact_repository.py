"""Memory Compact repository contracts."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime

from app.memory.domain.entities.memory_compact import MemoryCompact
from app.memory.domain.event_enum.memory_compact_enums import (
    MemoryCompactReviewVerdict,
    MemoryCompactStatus,
)


@dataclass(frozen=True, slots=True, kw_only=True)
class MemoryCompactSourceRefCreate:
    """Source ref fields accepted during compact creation."""

    source_type: str
    source_id: str
    title: str
    detail_path: str
    source_hash: str | None = None


@dataclass(frozen=True, slots=True, kw_only=True)
class MemoryCompactCreate:
    """Fields required to create a Memory Compact."""

    project: str | None
    covered_from: datetime
    covered_to: datetime
    markdown_body: str
    status: MemoryCompactStatus
    source_refs: list[MemoryCompactSourceRefCreate]
    review_verdict: MemoryCompactReviewVerdict | None = None
    review_score: int | None = None
    review_max_score: int | None = None
    reviewed_at: datetime | None = None


class IMemoryCompactRepository(ABC):
    """Persistence contract for Memory Compact artifacts."""

    @abstractmethod
    async def create(self, payload: MemoryCompactCreate) -> MemoryCompact:
        """Create a compact and its source refs.

        Args:
            payload: Memory Compact creation contract.

        Returns:
            Created Memory Compact entity.
        """

    @abstractmethod
    async def get(self, compact_id: str) -> MemoryCompact | None:
        """Read one compact by id.

        Args:
            compact_id: Memory Compact identifier.

        Returns:
            Matching compact, or None when absent.
        """

    @abstractmethod
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

    @abstractmethod
    async def current(self, *, project: str | None = None) -> MemoryCompact | None:
        """Read the current compact for a project.

        Args:
            project: Optional project filter; None addresses the default project.

        Returns:
            Current compact, or None when absent.
        """

    @abstractmethod
    async def mark_current(
        self,
        compact_id: str,
        *,
        review_verdict: MemoryCompactReviewVerdict | None = None,
        review_score: int | None = None,
        review_max_score: int | None = None,
        reviewed_at: datetime | None = None,
    ) -> MemoryCompact:
        """Mark one compact current and supersede previous current.

        Args:
            compact_id: Memory Compact identifier.
            review_verdict: Latest librarian review verdict for the promotion.
            review_score: Latest librarian review total score.
            review_max_score: Latest librarian review maximum score.
            reviewed_at: Review timestamp.

        Returns:
            Updated current compact.
        """

    @abstractmethod
    async def archive(self, compact_id: str) -> MemoryCompact:
        """Archive one compact.

        Args:
            compact_id: Memory Compact identifier.

        Returns:
            Archived compact.
        """

    @abstractmethod
    async def delete(self, compact_id: str) -> None:
        """Hard delete one compact and dependent source refs.

        Args:
            compact_id: Memory Compact identifier.

        Returns:
            None.
        """
