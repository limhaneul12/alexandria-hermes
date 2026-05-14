"""Agent router contract tests without provider API assignment."""

from __future__ import annotations

from datetime import UTC, datetime

from app.library.application.agent_service import AgentService
from app.library.domain.contracts.agent_contracts import AgentCreate, AgentUpdate
from app.library.domain.entities.read_models import AgentProfile
from app.library.domain.repositories.agent_repository import IAgentRepository
from app.main import app
from app.shared.types.extra_types import JSONValue
from fastapi.testclient import TestClient
from tests.library.interface.provider_overrides import override_library_provider


class FakeAgentRepository(IAgentRepository):
    """In-memory agent repository for router contract tests."""

    async def create(self, payload: AgentCreate) -> AgentProfile:
        """Create one agent profile."""
        return AgentProfile(
            id="00000000-0000-4000-8000-000000000601",
            name=payload.name,
            provider=payload.provider,
            description=payload.description,
            capabilities=payload.capabilities,
            preferred_librarian_provider=None,
            created_at=datetime(2026, 5, 12, 10, 0, tzinfo=UTC),
            updated_at=datetime(2026, 5, 12, 10, 0, tzinfo=UTC),
        )

    async def get(self, agent_id: str) -> AgentProfile | None:
        """Get one agent profile."""
        if agent_id != "00000000-0000-4000-8000-000000000601":
            return None
        return AgentProfile(
            id=agent_id,
            name="research-agent",
            provider="LOCAL",
            description="Finds reusable backend implementation guidance.",
            capabilities=["search", "summarize"],
            preferred_librarian_provider=None,
            created_at=datetime(2026, 5, 12, 10, 0, tzinfo=UTC),
            updated_at=datetime(2026, 5, 12, 10, 0, tzinfo=UTC),
        )

    async def list_all(self) -> list[AgentProfile]:
        """List all agent profiles."""
        profile = await self.get("00000000-0000-4000-8000-000000000601")
        return [] if profile is None else [profile]

    async def update(self, agent_id: str, payload: AgentUpdate) -> AgentProfile:
        """Patch profile data."""
        values = payload.to_record()
        return AgentProfile(
            id=agent_id,
            name="research-agent",
            provider="LOCAL",
            description=values.get("description")
            if isinstance(values.get("description"), str)
            else None,
            capabilities=values.get("capabilities")
            if isinstance(values.get("capabilities"), list)
            else ["search"],
            preferred_librarian_provider=None,
            created_at=datetime(2026, 5, 12, 10, 0, tzinfo=UTC),
            updated_at=datetime(2026, 5, 12, 10, 5, tzinfo=UTC),
        )

    async def delete(self, agent_id: str) -> None:
        """Delete one profile."""


def _agent_payload() -> dict[str, JSONValue]:
    """Return a valid agent request payload."""
    return {
        "name": "research-agent",
        "provider": "LOCAL",
        "description": "Finds reusable backend implementation guidance.",
        "capabilities": ["search", "summarize"],
    }


def _override_agent_service() -> AgentService:
    return AgentService(repository=FakeAgentRepository())


def test_create_agent_persists_profile_without_provider_assignment_api() -> None:
    """POST /agents should create an agent profile without API-provider coupling."""
    with override_library_provider("agent_service", _override_agent_service()):
        with TestClient(app, raise_server_exceptions=False) as client:
            response = client.post("/agents", json=_agent_payload())

    assert response.status_code == 201
    assert response.json() == {
        "id": "00000000-0000-4000-8000-000000000601",
        "name": "research-agent",
        "provider": "LOCAL",
        "description": "Finds reusable backend implementation guidance.",
        "capabilities": ["search", "summarize"],
        "created_at": "2026-05-12T10:00:00Z",
        "updated_at": "2026-05-12T10:00:00Z",
    }


def test_patch_agent_updates_profile_without_provider_assignment_api() -> None:
    """PATCH /agents/{id} should update profile text/capabilities only."""
    with override_library_provider("agent_service", _override_agent_service()):
        with TestClient(app, raise_server_exceptions=False) as client:
            response = client.patch(
                "/agents/00000000-0000-4000-8000-000000000601",
                json={"description": "Updated", "capabilities": ["search"]},
            )

    assert response.status_code == 200
    assert response.json()["description"] == "Updated"
    assert response.json()["capabilities"] == ["search"]
    assert "preferred_librarian_provider" not in response.json()


def test_get_agent_omits_provider_assignment_api_fields() -> None:
    """GET /agents/{id} should expose profile metadata only."""
    with override_library_provider("agent_service", _override_agent_service()):
        with TestClient(app, raise_server_exceptions=False) as client:
            response = client.get("/agents/00000000-0000-4000-8000-000000000601")

    assert response.status_code == 200
    assert "preferred_librarian_provider" not in response.json()
