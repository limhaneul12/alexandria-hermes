"""Agent router contract tests without provider API assignment."""

from __future__ import annotations

from datetime import UTC, datetime

from app.connections.domain.contracts.librarian_provider_contracts import (
    LibrarianProviderCreate,
    LibrarianProviderUpdate,
)
from app.connections.domain.entities.read_models import LibrarianProvider
from app.connections.domain.event_enum.provider_enums import (
    AuthType,
    ProviderSecretKey,
    ProviderType,
)
from app.connections.domain.repositories.librarian_repository import (
    ILibrarianProviderRepository,
    IProviderSecretRepository,
)
from app.librarian.application.agent_service import AgentService
from app.librarian.domain.contracts.agent_contracts import AgentCreate, AgentUpdate
from app.librarian.domain.entities.read_models import AgentProfile
from app.librarian.domain.repositories.agent_repository import IAgentRepository
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
            preferred_librarian_provider=payload.preferred_librarian_provider,
            preferred_librarian_model=payload.preferred_librarian_model,
            max_librarian_agents=payload.max_librarian_agents,
            librarian_role_prompt=payload.librarian_role_prompt,
            librarian_role=payload.librarian_role,
            librarian_specialties=payload.librarian_specialties,
            librarian_routing_priority=payload.librarian_routing_priority,
            librarian_enabled=payload.librarian_enabled,
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
            preferred_librarian_provider="00000000-0000-4000-8000-000000000777",
            preferred_librarian_model="gpt-5.5",
            max_librarian_agents=3,
            librarian_role_prompt="Act as a codebase librarian.",
            librarian_role="SPECIALIST",
            librarian_specialties=["search", "summarize"],
            librarian_routing_priority=20,
            librarian_enabled=True,
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
            name=values.get("name")
            if isinstance(values.get("name"), str)
            else "research-agent",
            provider=values.get("provider")
            if isinstance(values.get("provider"), str)
            else "LOCAL",
            description=values.get("description", None),
            capabilities=values.get("capabilities")
            if isinstance(values.get("capabilities"), list)
            else ["search"],
            preferred_librarian_provider=values.get(
                "preferred_librarian_provider", None
            ),
            preferred_librarian_model=values.get("preferred_librarian_model", None),
            max_librarian_agents=values.get("max_librarian_agents")
            if isinstance(values.get("max_librarian_agents"), int)
            else 1,
            librarian_role_prompt=values.get("librarian_role_prompt", None),
            librarian_role=values.get("librarian_role", "DEFAULT_SEARCH"),
            librarian_specialties=values.get("librarian_specialties", []),
            librarian_routing_priority=values.get("librarian_routing_priority", 100),
            librarian_enabled=values.get("librarian_enabled", True),
            created_at=datetime(2026, 5, 12, 10, 0, tzinfo=UTC),
            updated_at=datetime(2026, 5, 12, 10, 5, tzinfo=UTC),
        )

    async def delete(self, agent_id: str) -> None:
        """Delete one profile."""


class FakeProviderRepository(ILibrarianProviderRepository):
    """In-memory provider repository for executable profile validation."""

    async def create(self, payload: LibrarianProviderCreate) -> LibrarianProvider:
        """Create is unused by agent route tests."""
        raise NotImplementedError

    async def get(self, provider_id: str) -> LibrarianProvider | None:
        """Return enabled OAuth providers used by the agent profile tests."""
        if provider_id not in {
            "00000000-0000-4000-8000-000000000777",
            "00000000-0000-4000-8000-000000000888",
        }:
            return None
        return LibrarianProvider(
            id=provider_id,
            name="codex-oauth",
            provider_type=ProviderType.OPENAI_CODEX.value,
            auth_type=AuthType.OAUTH.value,
            enabled=True,
            config={},
            created_at=datetime(2026, 5, 12, 10, 0, tzinfo=UTC),
            updated_at=datetime(2026, 5, 12, 10, 0, tzinfo=UTC),
        )

    async def list_all(self) -> list[LibrarianProvider]:
        """List is unused by agent route tests."""
        raise NotImplementedError

    async def update(
        self, provider_id: str, payload: LibrarianProviderUpdate
    ) -> LibrarianProvider:
        """Update is unused by agent route tests."""
        raise NotImplementedError

    async def delete(self, provider_id: str) -> None:
        """Delete is unused by agent route tests."""
        raise NotImplementedError


class FakeProviderSecretRepository(IProviderSecretRepository):
    """In-memory provider secret repository for executable profile validation."""

    async def resolve(self, provider_id: str, key_name: str) -> str | None:
        """Return OAuth secrets needed for execution readiness."""
        if key_name == ProviderSecretKey.OAUTH_ACCESS_TOKEN.value:
            return "access-token"
        if key_name == ProviderSecretKey.OAUTH_EXPIRES_AT.value:
            return "2026-05-12T10:10:00+00:00"
        return None

    async def set_secret(self, *, provider_id: str, key_name: str, value: str) -> None:
        """Set secret is unused by agent route tests."""
        raise NotImplementedError

    async def delete_for_provider(self, provider_id: str, key_name: str) -> None:
        """Delete secret is unused by agent route tests."""
        raise NotImplementedError


def _agent_payload() -> dict[str, JSONValue]:
    """Return a valid agent request payload."""
    return {
        "name": "research-agent",
        "provider": "LOCAL",
        "description": "Finds reusable backend implementation guidance.",
        "capabilities": ["search", "summarize"],
        "preferred_librarian_provider": "00000000-0000-4000-8000-000000000777",
        "preferred_librarian_model": "gpt-5.5",
        "max_librarian_agents": 3,
        "librarian_role_prompt": "Act as a codebase librarian.",
        "librarian_role": "SPECIALIST",
        "librarian_specialties": ["search", "summarize"],
        "librarian_routing_priority": 20,
        "librarian_enabled": True,
    }


def _override_agent_service() -> AgentService:
    return AgentService(
        repository=FakeAgentRepository(),
        provider_repo=FakeProviderRepository(),
        secret_repo=FakeProviderSecretRepository(),
        now_provider=lambda: datetime(2026, 5, 12, 10, 0, tzinfo=UTC),
    )


def test_create_agent_persists_profile_without_provider_assignment_api() -> None:
    """POST /librarians/profiles should create an agent profile without API-provider coupling."""
    with (
        override_library_provider("agent_service", _override_agent_service()),
        TestClient(app, raise_server_exceptions=False) as client,
    ):
        response = client.post("/librarians/profiles", json=_agent_payload())

    assert response.status_code == 201
    assert response.json() == {
        "id": "00000000-0000-4000-8000-000000000601",
        "name": "research-agent",
        "provider": "LOCAL",
        "description": "Finds reusable backend implementation guidance.",
        "capabilities": ["search", "summarize"],
        "preferred_librarian_provider": "00000000-0000-4000-8000-000000000777",
        "preferred_librarian_model": "gpt-5.5",
        "max_librarian_agents": 3,
        "librarian_role_prompt": "Act as a codebase librarian.",
        "librarian_role": "SPECIALIST",
        "librarian_specialties": ["search", "summarize"],
        "librarian_routing_priority": 20,
        "librarian_enabled": True,
        "created_at": "2026-05-12T10:00:00Z",
        "updated_at": "2026-05-12T10:00:00Z",
    }


def test_patch_agent_updates_librarian_profile_assignment() -> None:
    """PATCH /librarians/profiles/{id} should update librarian profile settings."""
    with (
        override_library_provider("agent_service", _override_agent_service()),
        TestClient(app, raise_server_exceptions=False) as client,
    ):
        response = client.patch(
            "/librarians/profiles/00000000-0000-4000-8000-000000000601",
            json={
                "name": "review-agent",
                "description": "Updated",
                "capabilities": ["search"],
                "preferred_librarian_provider": (
                    "00000000-0000-4000-8000-000000000888"
                ),
                "preferred_librarian_model": "gpt-5.4",
                "max_librarian_agents": 2,
                "librarian_role_prompt": "Use project memory before web search.",
                "librarian_role": "QUALITY_REVIEWER",
                "librarian_specialties": ["security", "evidence"],
                "librarian_routing_priority": 5,
                "librarian_enabled": True,
            },
        )

    assert response.status_code == 200
    assert response.json()["name"] == "review-agent"
    assert response.json()["description"] == "Updated"
    assert response.json()["capabilities"] == ["search"]
    assert response.json()["preferred_librarian_provider"] == (
        "00000000-0000-4000-8000-000000000888"
    )
    assert response.json()["preferred_librarian_model"] == "gpt-5.4"
    assert response.json()["max_librarian_agents"] == 2
    assert response.json()["librarian_role_prompt"] == (
        "Use project memory before web search."
    )
    assert response.json()["librarian_role"] == "QUALITY_REVIEWER"
    assert response.json()["librarian_specialties"] == ["security", "evidence"]
    assert response.json()["librarian_routing_priority"] == 5
    assert response.json()["librarian_enabled"] is True


def test_patch_agent_rejects_empty_payload_when_no_fields_are_supplied() -> None:
    """PATCH /librarians/profiles/{id} should reject no-op profile updates."""
    with (
        override_library_provider("agent_service", _override_agent_service()),
        TestClient(app, raise_server_exceptions=False) as client,
    ):
        response = client.patch(
            "/librarians/profiles/00000000-0000-4000-8000-000000000601",
            json={},
        )

    assert response.status_code == 422


def test_patch_agent_rejects_null_values_for_required_profile_fields() -> None:
    """PATCH /librarians/profiles/{id} should reject nulls for non-nullable fields."""
    with (
        override_library_provider("agent_service", _override_agent_service()),
        TestClient(app, raise_server_exceptions=False) as client,
    ):
        response = client.patch(
            "/librarians/profiles/00000000-0000-4000-8000-000000000601",
            json={"name": None, "capabilities": None},
        )

    assert response.status_code == 422


def test_patch_agent_allows_clearing_nullable_librarian_profile_fields() -> None:
    """PATCH /librarians/profiles/{id} should let optional librarian profile fields clear."""
    with (
        override_library_provider("agent_service", _override_agent_service()),
        TestClient(app, raise_server_exceptions=False) as client,
    ):
        response = client.patch(
            "/librarians/profiles/00000000-0000-4000-8000-000000000601",
            json={
                "description": None,
                "preferred_librarian_provider": None,
                "preferred_librarian_model": None,
                "librarian_role_prompt": None,
            },
        )

    body = response.json()
    assert response.status_code == 200
    assert body["description"] is None
    assert body["preferred_librarian_provider"] is None
    assert body["preferred_librarian_model"] is None
    assert body["librarian_role_prompt"] is None


def test_get_agent_exposes_librarian_profile_assignment() -> None:
    """GET /librarians/profiles/{id} should expose configured librarian profile settings."""
    with (
        override_library_provider("agent_service", _override_agent_service()),
        TestClient(app, raise_server_exceptions=False) as client,
    ):
        response = client.get(
            "/librarians/profiles/00000000-0000-4000-8000-000000000601"
        )

    assert response.status_code == 200
    assert response.json()["preferred_librarian_provider"] == (
        "00000000-0000-4000-8000-000000000777"
    )
    assert response.json()["preferred_librarian_model"] == "gpt-5.5"
    assert response.json()["max_librarian_agents"] == 3
    assert response.json()["librarian_role_prompt"] == "Act as a codebase librarian."
    assert response.json()["librarian_role"] == "SPECIALIST"
    assert response.json()["librarian_specialties"] == ["search", "summarize"]
    assert response.json()["librarian_routing_priority"] == 20
    assert response.json()["librarian_enabled"] is True
