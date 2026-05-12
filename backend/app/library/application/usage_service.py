"""Usage tracking and analytics service."""

from __future__ import annotations

from dataclasses import dataclass

from app.library.domain.repositories.usage_repository import UsageRepository
from app.shared.types.extra_types import JSONValue


@dataclass(frozen=True)
class UsageService:
    """Service wrapper for usage history operations."""

    usage_repo: UsageRepository

    async def record_usage(self, payload: dict[str, JSONValue]) -> dict[str, JSONValue]:
        """Persist usage event and return response payload."""
        model = await self.usage_repo.create(payload=payload)
        return {
            "id": model.id,
            "item_id": model.item_id,
            "item_type": model.item_type,
            "agent_name": model.agent_name,
            "librarian_provider": model.librarian_provider,
            "selection_source": model.selection_source,
            "used_at": model.used_at,
            "success": model.success,
        }

    async def recent(self, *, limit: int = 20) -> list[dict[str, JSONValue]]:
        """Recent usage events."""
        rows = await self.usage_repo.recent(limit=limit)
        return [
            {
                "id": row.id,
                "item_id": row.item_id,
                "item_type": row.item_type,
                "agent_name": row.agent_name,
                "librarian_provider": row.librarian_provider,
                "used_at": row.used_at,
                "success": row.success,
                "selection_source": row.selection_source,
            }
            for row in rows
        ]

    async def popular(self, *, limit: int = 10) -> list[dict[str, JSONValue]]:
        """Top popular items by usage count."""
        data = await self.usage_repo.popular(limit=limit)
        return [{"item_id": item_id, "count": count} for item_id, count in data]

    async def popular_by_category(
        self, *, limit: int = 10
    ) -> list[dict[str, JSONValue]]:
        """Category-level usage summary."""
        data = await self.usage_repo.popular_by_category(limit=limit)
        return [
            {
                "category_id": category_id,
                "item_type": item_type,
                "count": count,
            }
            for category_id, item_type, count in data
        ]

    async def by_item(self, item_id: int) -> list[dict[str, JSONValue]]:
        """Usage history for one item."""
        rows = await self.usage_repo.list_by_item(item_id)
        return [
            {
                "id": row.id,
                "agent_name": row.agent_name,
                "query": row.query,
                "selection_source": row.selection_source,
                "used_at": row.used_at,
                "success": row.success,
            }
            for row in rows
        ]
