"""Usage repository abstraction."""

from __future__ import annotations

from abc import ABC, abstractmethod

from app.library.domain.entities.enums import SelectionSource
from app.library.domain.entities.read_models import UsageHistory
from app.shared.types.extra_types import JSONValue


class UsageRepository(ABC):
    """Persistence contract for usage logs."""

    @abstractmethod
    async def create(self, payload: dict[str, JSONValue]) -> UsageHistory:
        """Create one usage row."""

    @abstractmethod
    async def recent(self, *, limit: int = 20) -> list[UsageHistory]:
        """Return recent usage rows."""

    @abstractmethod
    async def popular(
        self, *, limit: int = 10, success_only: bool = True
    ) -> list[tuple[str, int]]:
        """Return top item IDs and count."""

    @abstractmethod
    async def popular_by_category(
        self,
        *,
        limit: int = 10,
    ) -> list[tuple[str, str, int]]:
        """Return category popularity using library item join."""

    @abstractmethod
    async def list_by_item(self, item_id: str) -> list[UsageHistory]:
        """Return logs for one item."""

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
        """Write one usage event."""
