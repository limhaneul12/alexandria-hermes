"""SQLAlchemy Memory Compact repository implementation."""

from __future__ import annotations

from datetime import UTC, datetime

from app.memory.domain.entities.memory_compact import (
    MemoryCompact,
    MemoryCompactSourceRef,
)
from app.memory.domain.event_enum.memory_compact_enums import (
    MemoryCompactStatus,
)
from app.memory.domain.repositories.memory_compact_repository import (
    IMemoryCompactRepository,
    MemoryCompactCreate,
)
from app.memory.infrastructure.models.memory_compact_models import (
    MemoryCompactORM,
    MemoryCompactSourceRefORM,
)
from app.shared.exceptions import MemoryCompactNotFoundError
from app.shared.types.types_convert_utils import aware_utc_datetime
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession


class SqlAlchemyMemoryCompactRepository(IMemoryCompactRepository):
    """Concrete repository for Memory Compact persistence."""

    def __init__(self, *, session: AsyncSession) -> None:
        """Initialize repository with a request session.

        Args:
            session: SQLAlchemy async session for the request.
        """
        self._session = session

    async def create(self, payload: MemoryCompactCreate) -> MemoryCompact:
        """Create one Memory Compact row and source refs.

        Args:
            payload: Memory Compact creation contract.

        Returns:
            Created Memory Compact entity.
        """
        now = datetime.now(UTC)
        if payload.status is MemoryCompactStatus.CURRENT:
            await self._supersede_current_project(payload.project, excluded_id=None)
        model = MemoryCompactORM(
            project=payload.project,
            covered_from=payload.covered_from,
            covered_to=payload.covered_to,
            markdown_body=payload.markdown_body,
            status=payload.status.value,
            created_at=now,
            updated_at=now,
            archived_at=None,
        )
        self._session.add(model)
        await self._session.flush()
        for source_ref in payload.source_refs:
            self._session.add(
                MemoryCompactSourceRefORM(
                    compact_id=model.id,
                    source_type=source_ref.source_type,
                    source_id=source_ref.source_id,
                    title=source_ref.title,
                    detail_path=source_ref.detail_path,
                )
            )
        await self._session.flush()
        return await self._read_model(model)

    async def get(self, compact_id: str) -> MemoryCompact | None:
        """Read one compact by id.

        Args:
            compact_id: Memory Compact identifier.

        Returns:
            Matching compact, or None when absent.
        """
        model = await self._session.get(MemoryCompactORM, compact_id)
        if model is None:
            return None
        return await self._read_model(model)

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
        statement = select(MemoryCompactORM)
        if project is not None:
            statement = statement.where(MemoryCompactORM.project == project)
        if status is not None:
            statement = statement.where(MemoryCompactORM.status == status.value)
        if covered_after is not None:
            statement = statement.where(MemoryCompactORM.covered_to >= covered_after)
        if covered_before is not None:
            statement = statement.where(MemoryCompactORM.covered_from <= covered_before)
        count = await self._session.scalar(
            select(func.count()).select_from(statement.subquery())
        )
        page = (
            statement.order_by(MemoryCompactORM.covered_to.desc())
            .offset(offset)
            .limit(limit)
        )
        rows = await self._session.execute(page)
        models = list(rows.scalars().all())
        return [await self._read_model(model) for model in models], int(count or 0)

    async def current(self, *, project: str | None = None) -> MemoryCompact | None:
        """Read current compact for a project.

        Args:
            project: Optional project filter; None addresses the default project.

        Returns:
            Current compact, or None when absent.
        """
        statement = select(MemoryCompactORM).where(
            MemoryCompactORM.status == MemoryCompactStatus.CURRENT.value
        )
        if project is None:
            statement = statement.where(MemoryCompactORM.project.is_(None))
        else:
            statement = statement.where(MemoryCompactORM.project == project)
        statement = statement.order_by(MemoryCompactORM.updated_at.desc()).limit(1)
        model = await self._session.scalar(statement)
        if model is None:
            return None
        return await self._read_model(model)

    async def mark_current(self, compact_id: str) -> MemoryCompact:
        """Mark one compact current and supersede prior current for project.

        Args:
            compact_id: Memory Compact identifier.

        Returns:
            Updated current compact.
        """
        model = await self._session.get(MemoryCompactORM, compact_id)
        if model is None:
            raise MemoryCompactNotFoundError(f"Memory compact not found: {compact_id}")
        await self._supersede_current_project(model.project, excluded_id=model.id)
        now = datetime.now(UTC)
        model.status = MemoryCompactStatus.CURRENT.value
        model.archived_at = None
        model.updated_at = now
        await self._session.flush()
        return await self._read_model(model)

    async def archive(self, compact_id: str) -> MemoryCompact:
        """Archive one compact.

        Args:
            compact_id: Memory Compact identifier.

        Returns:
            Archived compact.
        """
        model = await self._session.get(MemoryCompactORM, compact_id)
        if model is None:
            raise MemoryCompactNotFoundError(f"Memory compact not found: {compact_id}")
        now = datetime.now(UTC)
        model.status = MemoryCompactStatus.ARCHIVED.value
        model.archived_at = now
        model.updated_at = now
        await self._session.flush()
        return await self._read_model(model)

    async def _supersede_current_project(
        self,
        project: str | None,
        excluded_id: str | None,
    ) -> None:
        statement = select(MemoryCompactORM).where(
            MemoryCompactORM.status == MemoryCompactStatus.CURRENT.value
        )
        if excluded_id is not None:
            statement = statement.where(MemoryCompactORM.id != excluded_id)
        if project is None:
            statement = statement.where(MemoryCompactORM.project.is_(None))
        else:
            statement = statement.where(MemoryCompactORM.project == project)
        rows = await self._session.execute(statement)
        now = datetime.now(UTC)
        for model in rows.scalars().all():
            model.status = MemoryCompactStatus.SUPERSEDED.value
            model.updated_at = now
        await self._session.flush()

    async def _read_model(self, model: MemoryCompactORM) -> MemoryCompact:
        refs_result = await self._session.execute(
            select(MemoryCompactSourceRefORM)
            .where(MemoryCompactSourceRefORM.compact_id == model.id)
            .order_by(MemoryCompactSourceRefORM.id.asc())
        )
        refs = tuple(_map_source_ref(row) for row in refs_result.scalars().all())
        return MemoryCompact(
            id=model.id,
            project=model.project,
            covered_from=aware_utc_datetime(model.covered_from),
            covered_to=aware_utc_datetime(model.covered_to),
            markdown_body=model.markdown_body,
            status=MemoryCompactStatus(model.status),
            source_refs=refs,
            created_at=aware_utc_datetime(model.created_at),
            updated_at=aware_utc_datetime(model.updated_at),
            archived_at=aware_utc_datetime(model.archived_at)
            if model.archived_at is not None
            else None,
        )


def _map_source_ref(row: MemoryCompactSourceRefORM) -> MemoryCompactSourceRef:
    return MemoryCompactSourceRef(
        id=row.id,
        compact_id=row.compact_id,
        source_type=row.source_type,
        source_id=row.source_id,
        title=row.title,
        detail_path=row.detail_path,
    )
