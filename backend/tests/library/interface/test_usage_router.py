"""Usage router contract tests."""

from __future__ import annotations

from datetime import UTC, datetime

from app.library.application.usage_service import UsageService
from app.library.domain.entities.read_models import UsageHistory
from app.library.domain.repositories.usage_repository import UsageRepository
from app.library.interface.routers.dependencies import get_usage_service
from app.main import app
from app.shared.types.extra_types import JSONValue
from fastapi.testclient import TestClient


class FakeUsageRepository(UsageRepository):
    """In-memory usage repository for router contract tests."""

    def __init__(self) -> None:
        """Initialize deterministic usage events."""
        self.event = UsageHistory(
            id="00000000-0000-4000-8000-000000000099",
            item_id="00000000-0000-4000-8000-000000000010",
            item_type="SKILL",
            agent_name="research-agent",
            librarian_provider="default-openai",
            query="fastapi tests",
            selection_source="SEARCH",
            used_at=datetime(2026, 5, 12, 10, 0, tzinfo=UTC),
            success=True,
            feedback={"comment": "Useful result."},
        )

    async def create(self, payload: dict[str, JSONValue]) -> UsageHistory:
        """Create one usage row."""
        return UsageHistory(
            id=self.event.id,
            item_id=str(payload["item_id"]),
            item_type=str(payload["item_type"]),
            agent_name=str(payload["agent_name"]),
            librarian_provider=payload.get("librarian_provider")
            if isinstance(payload.get("librarian_provider"), str)
            else None,
            query=payload.get("query") if isinstance(payload.get("query"), str) else None,
            selection_source=str(payload["selection_source"]),
            used_at=self.event.used_at,
            success=bool(payload["success"]),
            feedback={"comment": "Useful result."},
        )

    async def recent(self, *, limit: int = 20) -> list[UsageHistory]:
        """Return recent usage rows."""
        return [self.event][:limit]

    async def popular(
        self, *, limit: int = 10, success_only: bool = True
    ) -> list[tuple[str, int]]:
        """Return top item IDs and counts."""
        return [(self.event.item_id, 1)][:limit]

    async def popular_by_category(
        self,
        *,
        limit: int = 10,
    ) -> list[tuple[str, str, int]]:
        """Return category popularity using library item join."""
        return [("00000000-0000-4000-8000-000000000002", "SKILL", 1)][:limit]

    async def list_by_item(self, item_id: str) -> list[UsageHistory]:
        """Return logs for one item."""
        return [self.event] if item_id == self.event.item_id else []

    async def record_event(
        self,
        *,
        item_id: str,
        item_type: str,
        agent_name: str,
        query: str | None,
        librarian_provider: str | None,
        selection_source: str,
        success: bool,
        feedback: str | None,
    ) -> None:
        """Write one usage event."""


def test_record_usage_persists_event_and_returns_created_record() -> None:
    """POST /usage should record one event and return the created usage record."""

    def override_usage_service() -> UsageService:
        return UsageService(usage_repo=FakeUsageRepository())

    app.dependency_overrides[get_usage_service] = override_usage_service
    try:
        with TestClient(app) as client:
            response = client.post(
                "/usage",
                json={
                    "item_id": "00000000-0000-4000-8000-000000000010",
                    "item_type": "SKILL",
                    "agent_name": "research-agent",
                    "librarian_provider": "default-openai",
                    "query": "fastapi tests",
                    "selection_source": "SEARCH",
                    "success": True,
                    "feedback": "Useful result.",
                },
            )
    finally:
        app.dependency_overrides.pop(get_usage_service, None)

    assert response.status_code == 201
    assert response.json() == {
        "id": "00000000-0000-4000-8000-000000000099",
        "item_id": "00000000-0000-4000-8000-000000000010",
        "item_type": "SKILL",
        "agent_name": "research-agent",
        "librarian_provider": "default-openai",
        "selection_source": "SEARCH",
        "used_at": "2026-05-12T10:00:00Z",
        "success": True,
    }



def test_item_usage_returns_complete_usage_records_when_item_has_history() -> None:
    """Item usage history should include full usage record fields."""

    def override_usage_service() -> UsageService:
        return UsageService(usage_repo=FakeUsageRepository())

    app.dependency_overrides[get_usage_service] = override_usage_service
    try:
        with TestClient(app, raise_server_exceptions=False) as client:
            response = client.get(
                "/usage/items/00000000-0000-4000-8000-000000000010"
            )
    finally:
        app.dependency_overrides.pop(get_usage_service, None)

    assert response.status_code == 200
    assert response.json() == [
        {
            "id": "00000000-0000-4000-8000-000000000099",
            "item_id": "00000000-0000-4000-8000-000000000010",
            "item_type": "SKILL",
            "agent_name": "research-agent",
            "librarian_provider": "default-openai",
            "selection_source": "SEARCH",
            "used_at": "2026-05-12T10:00:00Z",
            "success": True,
        }
    ]
