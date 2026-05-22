"""Application service for Memory Compact lifecycle."""

from __future__ import annotations

from datetime import datetime

from app.memory.domain.entities.memory_compact import MemoryCompact
from app.memory.domain.event_enum.memory_compact_enums import (
    MemoryCompactStatus,
)
from app.memory.domain.repositories.memory_compact_repository import (
    IMemoryCompactRepository,
    MemoryCompactCreate,
)
from app.shared.exceptions import (
    MemoryCompactNotFoundError,
    MemoryCompactValidationError,
)
from app.shared.types.types_convert_utils import enum_value


class MemoryCompactService:
    """Coordinate first-class durable Memory Compact artifacts."""

    def __init__(self, repository: IMemoryCompactRepository) -> None:
        """Initialize service dependencies.

        Args:
            repository: Persistence port for Memory Compact artifacts.
        """
        self._repository = repository

    async def create(self, payload: MemoryCompactCreate) -> MemoryCompact:
        """Create a compact and enforce lifecycle invariants.

        Args:
            payload: Validated Memory Compact creation contract.

        Returns:
            Created Memory Compact entity.
        """
        payload = MemoryCompactCreate(
            project=payload.project,
            covered_from=payload.covered_from,
            covered_to=payload.covered_to,
            markdown_body=payload.markdown_body,
            status=enum_value(payload.status, MemoryCompactStatus, "status"),
            source_refs=payload.source_refs,
        )
        self._validate_create(payload)
        return await self._repository.create(payload)

    async def get(self, compact_id: str) -> MemoryCompact:
        """Read one Memory Compact by id.

        Args:
            compact_id: Memory Compact identifier.

        Returns:
            Matching Memory Compact entity.
        """
        compact = await self._repository.get(compact_id)
        if compact is None:
            raise MemoryCompactNotFoundError(f"Memory compact not found: {compact_id}")
        return compact

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
        """List Memory Compacts.

        Args:
            project: Project filter.
            status: Lifecycle status filter.
            covered_after: Coverage-overlap lower bound.
            covered_before: Coverage-overlap upper bound.
            limit: Maximum number of rows to return.
            offset: Number of rows to skip.

        Returns:
            Page of Memory Compacts and the total matching count.
        """
        if status is not None:
            status = enum_value(status, MemoryCompactStatus, "status")
        bounded_limit = min(max(int(limit), 1), 200)
        bounded_offset = max(int(offset), 0)
        return await self._repository.list_compacts(
            project=project,
            status=status,
            covered_after=covered_after,
            covered_before=covered_before,
            limit=bounded_limit,
            offset=bounded_offset,
        )

    async def current(self, *, project: str | None = None) -> MemoryCompact:
        """Read the current compact for a project.

        Args:
            project: Optional project filter; None addresses the default project.

        Returns:
            Current Memory Compact entity.
        """
        compact = await self._repository.current(project=project)
        if compact is None:
            label = "default project" if project is None else project
            raise MemoryCompactNotFoundError(
                f"Current memory compact not found: {label}"
            )
        return compact

    async def mark_current(self, compact_id: str) -> MemoryCompact:
        """Mark one compact as current.

        Args:
            compact_id: Memory Compact identifier.

        Returns:
            Updated current Memory Compact entity.
        """
        compact = await self.get(compact_id)
        if not compact.source_refs:
            raise MemoryCompactValidationError(
                "Current memory compact requires source refs"
            )
        return await self._repository.mark_current(compact_id)

    async def archive(self, compact_id: str) -> MemoryCompact:
        """Archive one Memory Compact.

        Args:
            compact_id: Memory Compact identifier.

        Returns:
            Archived Memory Compact entity.
        """
        return await self._repository.archive(compact_id)

    async def delete(self, compact_id: str) -> None:
        """Hard delete one Memory Compact.

        Args:
            compact_id: Memory Compact identifier.

        Returns:
            None.
        """
        await self._repository.delete(compact_id)

    def _validate_create(self, payload: MemoryCompactCreate) -> None:
        if payload.covered_to < payload.covered_from:
            raise MemoryCompactValidationError("covered_to must be after covered_from")
        if not payload.markdown_body.strip():
            raise MemoryCompactValidationError("markdown_body is required")
        if payload.status is MemoryCompactStatus.CURRENT and not payload.source_refs:
            raise MemoryCompactValidationError(
                "Current memory compact requires source refs"
            )
