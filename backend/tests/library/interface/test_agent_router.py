"""Agent router contract tests for librarian provider assignment."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from app.library.application.agent_service import AgentService
from app.library.domain.entities.read_models import AgentProfile, LibrarianProvider
from app.library.domain.repositories.agent_repository import AgentRepository
from app.library.domain.repositories.librarian_repository import (
    LibrarianProviderRepository,
)
from app.library.interface.routers.dependencies import get_agent_service
from app.main import app
from app.shared.types.extra_types import JSONValue
from fastapi.testclient import TestClient

PROVIDER_ID = "00000000-0000-4000-8000-000000000501"
MISSING_PROVIDER_ID = "00000000-0000-4000-8000-000000000404"


class FakeAgentRepository(AgentRepository):
    """In-memory agent repository for router contract tests."""

    async def create(self, payload: dict[str, JSONValue]) -> AgentProfile:
        """Create one agent profile."""
        return AgentProfile(
            id="00000000-0000-4000-8000-000000000601",
            name=str(payload["name"]),
            provider=str(payload["provider"]),
            description=payload["description"]
            if isinstance(payload.get("description"), str)
            else None,
            capabilities=[item for item in payload["capabilities"] if isinstance(item, str)]
            if isinstance(payload.get("capabilities"), list)
            else [],
            preferred_librarian_provider=payload["preferred_librarian_provider"]
            if isinstance(payload.get("preferred_librarian_provider"), str)
            else None,
            created_at=datetime(2026, 5, 12, 10, 0, tzinfo=UTC),
            updated_at=datetime(2026, 5, 12, 10, 0, tzinfo=UTC),
        )

    async def get(self, agent_id: str) -> AgentProfile | None:
        """Get one agent profile."""
        return None

    async def list_all(self) -> list[AgentProfile]:
        """List all agent profiles."""
        return []

    async def update(self, agent_id: str, payload: dict[str, JSONValue]) -> AgentProfile:
        """Patch profile data."""
        return await self.create(
            {
                "name": "research-agent",
                "provider": "OPENAI",
                "description": None,
                "capabilities": ["search"],
                **payload,
            }
        )

    async def delete(self, agent_id: str) -> None:
        """Delete one profile."""


class FakeLibrarianProviderRepository(LibrarianProviderRepository):
    """In-memory librarian provider repository for assignment checks."""

    def __init__(self, *, enabled: bool = True, auth_type: str = "API_KEY") -> None:
        """Initialize provider state."""
        self.enabled = enabled
        self.auth_type = auth_type

    async def create(self, payload: dict[str, JSONValue]) -> LibrarianProvider:
        """Create a provider entry."""
        raise NotImplementedError

    async def get(self, provider_id: str) -> LibrarianProvider | None:
        """Get one provider."""
        if provider_id != PROVIDER_ID:
            return None
        return LibrarianProvider(
            id=PROVIDER_ID,
            name="default-openai",
            provider_type="OPENAI",
            auth_type=self.auth_type,
            enabled=self.enabled,
            config={"model": "gpt-5.5"},
            created_at=datetime(2026, 5, 12, 10, 0, tzinfo=UTC),
            updated_at=datetime(2026, 5, 12, 10, 0, tzinfo=UTC),
        )

    async def list_all(self) -> list[LibrarianProvider]:
        """List all providers."""
        provider = await self.get(PROVIDER_ID)
        return [] if provider is None else [provider]

    async def update(
        self, provider_id: str, payload: dict[str, JSONValue]
    ) -> LibrarianProvider:
        """Patch provider settings."""
        raise NotImplementedError

    async def delete(self, provider_id: str) -> None:
        """Delete one provider."""


def _agent_payload(provider_id: str | None = PROVIDER_ID) -> dict[str, JSONValue]:
    """Return a valid agent request payload."""
    return {
        "name": "research-agent",
        "provider": "OPENAI",
        "description": "Finds reusable backend implementation guidance.",
        "capabilities": ["search", "summarize"],
        "preferred_librarian_provider": provider_id,
    }


def test_create_agent_accepts_enabled_librarian_provider_assignment() -> None:
    """POST /agents should persist an enabled librarian provider assignment."""

    def override_agent_service() -> AgentService:
        return AgentService(
            repository=FakeAgentRepository(),
            librarian_provider_repo=FakeLibrarianProviderRepository(),
        )

    app.dependency_overrides[get_agent_service] = override_agent_service
    try:
        with TestClient(app, raise_server_exceptions=False) as client:
            response = client.post("/agents", json=_agent_payload())
    finally:
        app.dependency_overrides.pop(get_agent_service, None)

    assert response.status_code == 201
    assert response.json() == {
        "id": "00000000-0000-4000-8000-000000000601",
        "name": "research-agent",
        "provider": "OPENAI",
        "description": "Finds reusable backend implementation guidance.",
        "capabilities": ["search", "summarize"],
        "preferred_librarian_provider": PROVIDER_ID,
        "created_at": "2026-05-12T10:00:00Z",
        "updated_at": "2026-05-12T10:00:00Z",
    }


@pytest.mark.parametrize("auth_type", ["API_KEY", "OAUTH"])
def test_patch_agent_accepts_enabled_librarian_provider_assignment(
    auth_type: str,
) -> None:
    """PATCH /agents/{id} should assign enabled API_KEY/OAUTH providers."""

    def override_agent_service() -> AgentService:
        return AgentService(
            repository=FakeAgentRepository(),
            librarian_provider_repo=FakeLibrarianProviderRepository(
                auth_type=auth_type
            ),
        )

    app.dependency_overrides[get_agent_service] = override_agent_service
    try:
        with TestClient(app, raise_server_exceptions=False) as client:
            response = client.patch(
                "/agents/00000000-0000-4000-8000-000000000601",
                json={"preferred_librarian_provider": PROVIDER_ID},
            )
    finally:
        app.dependency_overrides.pop(get_agent_service, None)

    assert response.status_code == 200
    body = response.json()
    assert body["preferred_librarian_provider"] == PROVIDER_ID
    assert "api_key" not in body
    assert "oauth_access_token" not in body


def test_patch_agent_clears_librarian_provider_assignment() -> None:
    """PATCH /agents/{id} should clear assignment when provider value is null."""

    def override_agent_service() -> AgentService:
        return AgentService(
            repository=FakeAgentRepository(),
            librarian_provider_repo=FakeLibrarianProviderRepository(),
        )

    app.dependency_overrides[get_agent_service] = override_agent_service
    try:
        with TestClient(app, raise_server_exceptions=False) as client:
            response = client.patch(
                "/agents/00000000-0000-4000-8000-000000000601",
                json={"preferred_librarian_provider": None},
            )
    finally:
        app.dependency_overrides.pop(get_agent_service, None)

    assert response.status_code == 200
    assert response.json()["preferred_librarian_provider"] is None


def test_create_agent_rejects_missing_librarian_provider_assignment() -> None:
    """POST /agents should reject assignment to an unknown librarian provider."""

    def override_agent_service() -> AgentService:
        return AgentService(
            repository=FakeAgentRepository(),
            librarian_provider_repo=FakeLibrarianProviderRepository(),
        )

    app.dependency_overrides[get_agent_service] = override_agent_service
    try:
        with TestClient(app, raise_server_exceptions=False) as client:
            response = client.post(
                "/agents",
                json=_agent_payload(MISSING_PROVIDER_ID),
            )
    finally:
        app.dependency_overrides.pop(get_agent_service, None)

    assert response.status_code == 400
    assert response.json() == {"detail": "Librarian provider not found"}


def test_create_agent_rejects_disabled_librarian_provider_assignment() -> None:
    """POST /agents should reject assignment to a disabled librarian provider."""

    def override_agent_service() -> AgentService:
        return AgentService(
            repository=FakeAgentRepository(),
            librarian_provider_repo=FakeLibrarianProviderRepository(enabled=False),
        )

    app.dependency_overrides[get_agent_service] = override_agent_service
    try:
        with TestClient(app, raise_server_exceptions=False) as client:
            response = client.post("/agents", json=_agent_payload())
    finally:
        app.dependency_overrides.pop(get_agent_service, None)

    assert response.status_code == 400
    assert response.json() == {"detail": "Librarian provider is disabled"}
