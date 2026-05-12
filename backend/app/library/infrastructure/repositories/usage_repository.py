"""SQLAlchemy usage-history repository implementation."""

from __future__ import annotations

from datetime import UTC, datetime

from app.library.domain.entities.enums import SelectionSource
from app.library.domain.entities.read_models import UsageHistory
from app.library.domain.repositories.usage_repository import UsageRepository
from app.library.infrastructure.models.item import LibraryItemORM
from app.library.infrastructure.models.usage import UsageHistoryORM
from app.shared.types.extra_types import JSONValue
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession


def _feedback_from(row: UsageHistoryORM) -> dict[str, JSONValue] | None:
    """Return typed feedback payload from an ORM row."""
    feedback = row.feedback
    return feedback if isinstance(feedback, dict) else None


def _to_read_model(row: UsageHistoryORM) -> UsageHistory:
    """Map a usage ORM row into the domain read model."""
    return UsageHistory(
        id=row.id,
        item_id=row.item_id,
        item_type=row.item_type,
        agent_name=row.agent_name,
        librarian_provider=row.librarian_provider,
        query=row.query,
        selection_source=row.selection_source,
        used_at=row.used_at,
        success=row.success,
        feedback=_feedback_from(row),
    )


class SqlAlchemyUsageRepository(UsageRepository):
    """Persist and query usage history with aggregates."""

    def __init__(self, *, session: AsyncSession) -> None:
        """Initialize repository.

        Args:
            session: Active AsyncSession.
        """
        self._session = session

    async def create(self, payload: dict[str, JSONValue]) -> UsageHistory:
        """Persist usage payload."""
        model = UsageHistoryORM(**payload)
        self._session.add(model)
        await self._session.flush()
        return _to_read_model(model)

    async def recent(self, *, limit: int = 20) -> list[UsageHistory]:
        """Return latest usage rows."""
        rows = await self._session.execute(
            select(UsageHistoryORM)
            .order_by(UsageHistoryORM.used_at.desc())
            .limit(limit)
        )
        return [_to_read_model(row) for row in rows.scalars().all()]

    async def popular(
        self, *, limit: int = 10, success_only: bool = True
    ) -> list[tuple[int, int]]:
        """Return most-used item IDs and counts."""
        query = (
            select(
                UsageHistoryORM.item_id,
                func.count(UsageHistoryORM.id).label("usage_count"),
            )
            .group_by(UsageHistoryORM.item_id)
            .order_by(func.count(UsageHistoryORM.id).desc())
            .limit(limit)
        )
        if success_only:
            query = query.where(UsageHistoryORM.success.is_(True))

        result = await self._session.execute(query)
        return [(int(row.item_id), int(row.usage_count)) for row in result.all()]

    async def popular_by_category(
        self, *, limit: int = 10
    ) -> list[tuple[int, str, int]]:
        """Return category-level popularity."""
        query = (
            select(
                LibraryItemORM.category_id,
                LibraryItemORM.item_type,
                func.count(UsageHistoryORM.id).label("usage_count"),
            )
            .join(
                LibraryItemORM,
                LibraryItemORM.id == UsageHistoryORM.item_id,
            )
            .where(LibraryItemORM.category_id.is_not(None))
            .group_by(LibraryItemORM.category_id, LibraryItemORM.item_type)
            .order_by(func.count(UsageHistoryORM.id).desc())
            .limit(limit)
        )
        rows = await self._session.execute(query)
        return [
            (
                int(category_id) if category_id is not None else 0,
                item_type,
                int(count),
            )
            for category_id, item_type, count in rows.all()
        ]

    async def list_by_item(self, item_id: int) -> list[UsageHistory]:
        """Return usage events for one item."""
        rows = await self._session.execute(
            select(UsageHistoryORM)
            .where(UsageHistoryORM.item_id == item_id)
            .order_by(UsageHistoryORM.used_at.desc())
        )
        return [_to_read_model(row) for row in rows.scalars().all()]

    async def record_event(
        self,
        *,
        item_id: int,
        item_type: str,
        agent_name: str,
        query: str | None,
        librarian_provider: str | None,
        selection_source: SelectionSource,
        success: bool,
        feedback: str | None,
    ) -> None:
        """Create a usage row and return quickly."""
        await self.create(
            {
                "item_id": item_id,
                "item_type": item_type,
                "agent_name": agent_name,
                "librarian_provider": librarian_provider,
                "query": query,
                "selection_source": selection_source.value,
                "used_at": datetime.now(UTC),
                "success": success,
                "feedback": {
                    "comment": feedback,
                }
                if feedback
                else None,
            }
        )
