"""Agent service behavior tests."""

from __future__ import annotations

from datetime import UTC, datetime

import anyio
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
from app.librarian.domain.event_enum.collaboration_enums import LibrarianProfileRole
from app.librarian.domain.repositories.agent_repository import IAgentRepository
from app.librarian.domain.types.agent_payload_types import AgentUpdateValues


def _agent_profile(agent_id: str = "agent-1") -> AgentProfile:
    """Return a stable agent profile for service tests.

    Args:
        agent_id: Identifier to place on the read model.

    Returns:
        Agent profile read model.
    """
    return AgentProfile(
        id=agent_id,
        name="research-agent",
        provider="LOCAL",
        description="Searches project memory.",
        capabilities=["search"],
        preferred_librarian_provider=None,
        preferred_librarian_model=None,
        max_librarian_agents=1,
        librarian_role_prompt=None,
        librarian_role=LibrarianProfileRole.DEFAULT_SEARCH,
        librarian_specialties=[],
        librarian_routing_priority=100,
        librarian_enabled=True,
        created_at=datetime(2026, 5, 12, 10, 0, tzinfo=UTC),
        updated_at=datetime(2026, 5, 12, 10, 5, tzinfo=UTC),
    )


class CapturingAgentRepository(IAgentRepository):
    """Repository fake that captures update values."""

    def __init__(self) -> None:
        """Initialize captured state."""
        self.updated_agent_id: str | None = None
        self.updated_values: AgentUpdateValues | None = None

    async def create(self, payload: AgentCreate) -> AgentProfile:
        """Create is unused by these service tests."""
        raise NotImplementedError

    async def get(self, agent_id: str) -> AgentProfile | None:
        """Get is unused by these service tests."""
        return _agent_profile(agent_id)

    async def list_all(self) -> list[AgentProfile]:
        """List is unused by these service tests."""
        return []

    async def update(self, agent_id: str, payload: AgentUpdate) -> AgentProfile:
        """Capture patch values and return a stable profile.

        Args:
            agent_id: Target agent identifier.
            payload: Patch command produced by the service.

        Returns:
            Stable profile read model.
        """
        self.updated_agent_id = agent_id
        self.updated_values = payload.values
        return _agent_profile(agent_id)

    async def delete(self, agent_id: str) -> None:
        """Delete is unused by these service tests."""


class CapturingProviderRepository(ILibrarianProviderRepository):
    """Provider fake that records executable-provider checks."""

    def __init__(self) -> None:
        """Initialize captured provider lookups."""
        self.requested_provider_ids: list[str] = []

    async def create(self, payload: LibrarianProviderCreate) -> LibrarianProvider:
        """Create is unused by these service tests."""
        raise NotImplementedError

    async def get(self, provider_id: str) -> LibrarianProvider | None:
        """Return an enabled OAuth provider for concrete assignments.

        Args:
            provider_id: Requested provider identifier.

        Returns:
            Provider read model for the requested identifier.
        """
        self.requested_provider_ids.append(provider_id)
        return LibrarianProvider(
            id=provider_id,
            name="codex-oauth",
            provider_type=ProviderType.OPENAI_CODEX,
            auth_type=AuthType.OAUTH,
            enabled=True,
            config={},
            created_at=datetime(2026, 5, 12, 10, 0, tzinfo=UTC),
            updated_at=datetime(2026, 5, 12, 10, 0, tzinfo=UTC),
        )

    async def list_all(self) -> list[LibrarianProvider]:
        """List is unused by these service tests."""
        return []

    async def update(
        self, provider_id: str, payload: LibrarianProviderUpdate
    ) -> LibrarianProvider:
        """Update is unused by these service tests."""
        raise NotImplementedError

    async def delete(self, provider_id: str) -> None:
        """Delete is unused by these service tests."""


class NameAliasProviderRepository(CapturingProviderRepository):
    """Provider fake that requires list fallback for name aliases."""

    async def get(self, provider_id: str) -> LibrarianProvider | None:
        """Return no direct id match while recording the lookup."""
        self.requested_provider_ids.append(provider_id)
        return None

    async def list_all(self) -> list[LibrarianProvider]:
        """Return one provider whose name matches the user-facing alias."""
        return [
            LibrarianProvider(
                id="provider-1",
                name="codex-oauth",
                provider_type=ProviderType.OPENAI_CODEX,
                auth_type=AuthType.OAUTH,
                enabled=True,
                config={},
                created_at=datetime(2026, 5, 12, 10, 0, tzinfo=UTC),
                updated_at=datetime(2026, 5, 12, 10, 0, tzinfo=UTC),
            )
        ]


class CapturingSecretRepository(IProviderSecretRepository):
    """Secret fake that records provider credential checks."""

    def __init__(self) -> None:
        """Initialize captured secret lookups."""
        self.resolved_keys: list[str] = []

    async def resolve(self, provider_id: str, key_name: str) -> str | None:
        """Return OAuth execution secrets for provider readiness.

        Args:
            provider_id: Provider identifier.
            key_name: Secret key name.

        Returns:
            Secret value when the service requests an executable OAuth secret.
        """
        self.resolved_keys.append(key_name)
        if key_name == ProviderSecretKey.OAUTH_ACCESS_TOKEN.value:
            return "access-token"
        if key_name == ProviderSecretKey.OAUTH_EXPIRES_AT.value:
            return "2026-05-12T10:10:00+00:00"
        return None

    async def set_secret(self, *, provider_id: str, key_name: str, value: str) -> None:
        """Set secret is unused by these service tests."""
        raise NotImplementedError

    async def delete_for_provider(self, provider_id: str, key_name: str) -> None:
        """Delete secret is unused by these service tests."""


def _service(
    *,
    agent_repo: CapturingAgentRepository,
    provider_repo: CapturingProviderRepository,
    secret_repo: CapturingSecretRepository,
) -> AgentService:
    """Build an agent service with deterministic dependencies.

    Args:
        agent_repo: Capturing agent repository fake.
        provider_repo: Capturing provider repository fake.
        secret_repo: Capturing secret repository fake.

    Returns:
        Agent service under test.
    """
    return AgentService(
        repository=agent_repo,
        provider_repo=provider_repo,
        secret_repo=secret_repo,
        now_provider=lambda: datetime(2026, 5, 12, 10, 0, tzinfo=UTC),
    )


def test_update_agent_preserves_nullable_clears_and_normalizes_role() -> None:
    """Patch updates should keep clear requests and normalize enum values."""

    async def scenario() -> None:
        agent_repo = CapturingAgentRepository()
        provider_repo = CapturingProviderRepository()
        secret_repo = CapturingSecretRepository()
        service = _service(
            agent_repo=agent_repo,
            provider_repo=provider_repo,
            secret_repo=secret_repo,
        )

        await service.update_agent(
            "agent-1",
            {
                "description": None,
                "preferred_librarian_provider": None,
                "librarian_role": "QUALITY_REVIEWER",
            },
        )

        assert agent_repo.updated_values == {
            "description": None,
            "preferred_librarian_provider": None,
            "librarian_role": LibrarianProfileRole.QUALITY_REVIEWER,
        }
        assert provider_repo.requested_provider_ids == []
        assert secret_repo.resolved_keys == []

    anyio.run(scenario)


def test_update_agent_checks_provider_execution_when_provider_is_assigned() -> None:
    """Concrete preferred providers should be executable before persistence."""

    async def scenario() -> None:
        agent_repo = CapturingAgentRepository()
        provider_repo = CapturingProviderRepository()
        secret_repo = CapturingSecretRepository()
        service = _service(
            agent_repo=agent_repo,
            provider_repo=provider_repo,
            secret_repo=secret_repo,
        )

        await service.update_agent(
            "agent-1",
            {"preferred_librarian_provider": "provider-1"},
        )

        assert agent_repo.updated_values == {
            "preferred_librarian_provider": "provider-1"
        }
        assert provider_repo.requested_provider_ids == ["provider-1"]
        assert secret_repo.resolved_keys == [
            ProviderSecretKey.OAUTH_REFRESH_TOKEN.value,
            ProviderSecretKey.OAUTH_ACCESS_TOKEN.value,
            ProviderSecretKey.OAUTH_EXPIRES_AT.value,
        ]

    anyio.run(scenario)


def test_update_agent_accepts_executable_provider_name_alias() -> None:
    """Concrete preferred providers may be supplied by user-facing provider name."""

    async def scenario() -> None:
        agent_repo = CapturingAgentRepository()
        provider_repo = NameAliasProviderRepository()
        secret_repo = CapturingSecretRepository()
        service = _service(
            agent_repo=agent_repo,
            provider_repo=provider_repo,
            secret_repo=secret_repo,
        )

        await service.update_agent(
            "agent-1",
            {"preferred_librarian_provider": "codex-oauth"},
        )

        assert agent_repo.updated_values == {
            "preferred_librarian_provider": "codex-oauth"
        }
        assert provider_repo.requested_provider_ids == ["codex-oauth"]
        assert secret_repo.resolved_keys == [
            ProviderSecretKey.OAUTH_REFRESH_TOKEN.value,
            ProviderSecretKey.OAUTH_ACCESS_TOKEN.value,
            ProviderSecretKey.OAUTH_EXPIRES_AT.value,
        ]

    anyio.run(scenario)
