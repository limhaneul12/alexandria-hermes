"""SQLAlchemy usage-history repository implementation."""

from __future__ import annotations

from datetime import UTC, datetime

from app.library.domain.contracts.usage_contracts import UsageCreate
from app.library.domain.entities.read_models import UsageHistory
from app.library.domain.event_enum.usage_enums import SelectionSource
from app.library.domain.repositories.usage_repository import IUsageRepository
from app.library.domain.types.usage_payload_types import (
    PopularByCategoryRows,
    PopularItemRows,
    UsageFeedbackPayload,
)
from app.library.infrastructure.models.item_models import LibraryItemORM
from app.library.infrastructure.models.usage_models import UsageHistoryORM
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession


def _feedback_from(row: UsageHistoryORM) -> UsageFeedbackPayload | None:
    """Return typed feedback payload from an ORM row."""
    feedback = row.feedback
    if feedback is None:
        return None
    return UsageFeedbackPayload(**feedback)


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


class SqlAlchemyUsageRepository(IUsageRepository):
    """Persist and query usage history with aggregates."""

    def __init__(self, *, session: AsyncSession) -> None:
        """Initialize repository.

        Args:
            session: Active AsyncSession.
        """
        self._session = session

    async def create(self, payload: UsageCreate) -> UsageHistory:
        """Persist usage payload.

        Args:
            payload [UsageCreate]: Value supplied to create.

        Returns:
            UsageHistory: Value produced by create.
        """
        model = UsageHistoryORM(**payload.to_record())
        self._session.add(model)
        await self._session.flush()
        return _to_read_model(model)

    async def recent(self, *, limit: int = 20) -> list[UsageHistory]:
        """Return latest usage rows.

        Args:
            limit [int]: Value supplied to recent.

        Returns:
            list[UsageHistory]: Value produced by recent.
        """
        rows = await self._session.execute(
            select(UsageHistoryORM)
            .order_by(UsageHistoryORM.used_at.desc())
            .limit(limit)
        )
        return [_to_read_model(row) for row in rows.scalars().all()]

    async def popular(
        self, *, limit: int = 10, success_only: bool = True
    ) -> PopularItemRows:
        """Return most-used item IDs and counts.

        Args:
            limit [int]: Value supplied to popular.
            success_only [bool]: Value supplied to popular.

        Returns:
            PopularItemRows: Value produced by popular.
        """
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
        return [(str(row.item_id), int(row.usage_count)) for row in result.all()]

    async def popular_by_category(self, *, limit: int = 10) -> PopularByCategoryRows:
        """Return category-level popularity.

        Args:
            limit [int]: Value supplied to popular_by_category.

        Returns:
            PopularByCategoryRows: Value produced by popular_by_category.
        """
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
                str(category_id),
                item_type,
                int(count),
            )
            for category_id, item_type, count in rows.all()
        ]

    async def list_by_item(self, item_id: str) -> list[UsageHistory]:
        """Return usage events for one item.

        Args:
            item_id [str]: Value supplied to list_by_item.

        Returns:
            list[UsageHistory]: Value produced by list_by_item.
        """
        rows = await self._session.execute(
            select(UsageHistoryORM)
            .where(UsageHistoryORM.item_id == item_id)
            .order_by(UsageHistoryORM.used_at.desc())
        )
        return [_to_read_model(row) for row in rows.scalars().all()]

    async def record_event(
        self,
        *,
        item_id: str,
        item_type: str,
        agent_name: str,
        query: str | None,
        librarian_provider: str | None,
        selection_source: SelectionSource,
        success: bool,
        feedback: str | None,
    ) -> None:
        """Create a usage row and return quickly.

        Args:
            item_id [str]: Value supplied to record_event.
            item_type [str]: Value supplied to record_event.
            agent_name [str]: Value supplied to record_event.
            query [str | None]: Value supplied to record_event.
            librarian_provider [str | None]: Value supplied to record_event.
            selection_source [SelectionSource]: Value supplied to record_event.
            success [bool]: Value supplied to record_event.
            feedback [str | None]: Value supplied to record_event.
        """
        feedback_payload: UsageFeedbackPayload | None = (
            {"comment": feedback} if feedback else None
        )
        await self.create(
            UsageCreate(
                item_id=item_id,
                item_type=item_type,
                agent_name=agent_name,
                librarian_provider=librarian_provider,
                query=query,
                selection_source=selection_source,
                used_at=datetime.now(UTC),
                success=success,
                feedback=feedback_payload,
            )
        )
