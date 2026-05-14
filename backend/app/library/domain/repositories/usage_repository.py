"""Usage repository abstraction."""

from __future__ import annotations

from abc import ABC, abstractmethod

from app.library.domain.contracts.usage_contracts import UsageCreate
from app.library.domain.entities.read_models import UsageHistory
from app.library.domain.event_enum.usage_enums import SelectionSource
from app.library.domain.types.usage_payload_types import (
    PopularByCategoryRows,
    PopularItemRows,
)


class IUsageRepository(ABC):
    """Persistence contract for usage logs."""

    @abstractmethod
    async def create(self, payload: UsageCreate) -> UsageHistory:
        """Create one usage row.

        Args:
            payload [UsageCreate]: Value supplied to create.

        Returns:
            UsageHistory: Value produced by create.
        """

    @abstractmethod
    async def recent(self, *, limit: int = 20) -> list[UsageHistory]:
        """Return recent usage rows.

        Args:
            limit [int]: Value supplied to recent.

        Returns:
            list[UsageHistory]: Value produced by recent.
        """

    @abstractmethod
    async def popular(
        self, *, limit: int = 10, success_only: bool = True
    ) -> PopularItemRows:
        """Return top item IDs and count.

        Args:
            limit [int]: Value supplied to popular.
            success_only [bool]: Value supplied to popular.

        Returns:
            PopularItemRows: Value produced by popular.
        """

    @abstractmethod
    async def popular_by_category(
        self,
        *,
        limit: int = 10,
    ) -> PopularByCategoryRows:
        """Return category popularity using library item join.

        Args:
            limit [int]: Value supplied to popular_by_category.

        Returns:
            PopularByCategoryRows: Value produced by popular_by_category.
        """

    @abstractmethod
    async def list_by_item(self, item_id: str) -> list[UsageHistory]:
        """Return logs for one item.

        Args:
            item_id [str]: Value supplied to list_by_item.

        Returns:
            list[UsageHistory]: Value produced by list_by_item.
        """

    @abstractmethod
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
        """Write one usage event.

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
