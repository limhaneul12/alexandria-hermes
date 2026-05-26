"""Agent profile service."""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime

from app.connections.domain.entities.read_models import LibrarianProvider
from app.connections.domain.repositories.librarian_repository import (
    ILibrarianProviderRepository,
    IProviderSecretRepository,
)
from app.librarian.application.provider_execution_policy import (
    provider_can_execute,
)
from app.librarian.domain.contracts.agent_contracts import AgentCreate, AgentUpdate
from app.librarian.domain.entities.read_models import AgentProfile
from app.librarian.domain.event_enum.collaboration_enums import LibrarianProfileRole
from app.librarian.domain.repositories.agent_repository import IAgentRepository
from app.librarian.domain.types.agent_payload_types import (
    AgentCreatePayload,
    AgentUpdatePayload,
    AgentUpdateValues,
)
from app.shared.exceptions import (
    LibrarianProviderUnsupportedError,
    LibrarianResourceNotFoundError,
)
from app.shared.types.types_convert_utils import (
    enum_value,
    now_utc,
)


def _profile_role_value(
    value: LibrarianProfileRole | str,
) -> LibrarianProfileRole:
    """Normalize profile role from public input.

    Args:
        value: Interface payload value to narrow.

    Returns:
        LibrarianProfileRole: Valid librarian profile role.
    """
    return enum_value(value, LibrarianProfileRole, "librarian_role")


def _agent_update_values(payload: AgentUpdatePayload) -> AgentUpdateValues:
    """Normalize public agent patch fields into an explicit update contract.

    Args:
        payload: Partial agent patch payload.

    Returns:
        AgentUpdateValues: Typed patch values accepted by the repository.
    """
    builder = _AgentUpdateValueBuilder(payload)
    return builder.build()


class _AgentUpdateValueBuilder:
    """Build repository-safe agent update values from a boundary payload."""

    __slots__ = ("_payload", "_values")

    def __init__(self, payload: AgentUpdatePayload) -> None:
        """Initialize the pure patch-value builder.

        Args:
            payload: Partial agent patch payload from the interface schema.
        """
        self._payload = payload
        self._values: AgentUpdateValues = {}

    def build(self) -> AgentUpdateValues:
        """Return normalized update values while preserving key presence.

        Returns:
            AgentUpdateValues: Repository-safe patch values.
        """
        self._apply_identity_fields()
        self._apply_librarian_preference_fields()
        self._apply_librarian_profile_fields()
        return self._values

    def _apply_identity_fields(self) -> None:
        if "name" in self._payload:
            self._values["name"] = self._payload["name"]
        if "provider" in self._payload:
            self._values["provider"] = self._payload["provider"]
        if "description" in self._payload:
            self._values["description"] = self._payload["description"]
        if "capabilities" in self._payload:
            self._values["capabilities"] = self._payload["capabilities"]

    def _apply_librarian_preference_fields(self) -> None:
        if "preferred_librarian_provider" in self._payload:
            self._values["preferred_librarian_provider"] = self._payload[
                "preferred_librarian_provider"
            ]
        if "preferred_librarian_model" in self._payload:
            self._values["preferred_librarian_model"] = self._payload[
                "preferred_librarian_model"
            ]
        if "max_librarian_agents" in self._payload:
            self._values["max_librarian_agents"] = self._payload["max_librarian_agents"]
        if "librarian_role_prompt" in self._payload:
            self._values["librarian_role_prompt"] = self._payload[
                "librarian_role_prompt"
            ]

    def _apply_librarian_profile_fields(self) -> None:
        if "librarian_role" in self._payload:
            self._values["librarian_role"] = _profile_role_value(
                self._payload["librarian_role"]
            )
        if "librarian_specialties" in self._payload:
            self._values["librarian_specialties"] = self._payload[
                "librarian_specialties"
            ]
        if "librarian_routing_priority" in self._payload:
            self._values["librarian_routing_priority"] = self._payload[
                "librarian_routing_priority"
            ]
        if "librarian_enabled" in self._payload:
            self._values["librarian_enabled"] = self._payload["librarian_enabled"]


class AgentService:
    """Application service for CRUD on agent profiles."""

    def __init__(
        self,
        repository: IAgentRepository,
        provider_repo: ILibrarianProviderRepository,
        secret_repo: IProviderSecretRepository,
        now_provider: Callable[[], datetime] = now_utc,
    ) -> None:
        """Initialize agent service dependencies.

        Args:
            repository: Agent persistence repository.
            provider_repo: Librarian provider repository.
            secret_repo: Librarian provider secret repository.
            now_provider: Clock boundary for provider executable checks.
        """
        self.repository = repository
        self.provider_repo = provider_repo
        self.secret_repo = secret_repo
        self.now_provider = now_provider

    async def list_agents(self) -> list[AgentProfile]:
        """List all agent profiles.

        Returns:
            list[AgentProfile]: Agent profiles ordered by repository policy.
        """
        return await self.repository.list_all()

    async def get_agent(self, agent_id: str) -> AgentProfile | None:
        """Read one agent profile.

        Args:
            agent_id: Target agent identifier.

        Returns:
            AgentProfile | None: Matching agent profile, or ``None`` when absent.
        """
        return await self.repository.get(agent_id)

    async def create_agent(self, payload: AgentCreatePayload) -> AgentProfile:
        """Create one agent profile from an interface payload.

        Args:
            payload: Validated interface payload containing agent creation fields.

        Returns:
            AgentProfile: Persisted agent profile.
        """
        preferred_provider_id = payload["preferred_librarian_provider"]
        await self._ensure_executable_provider(preferred_provider_id)
        return await self.repository.create(
            AgentCreate(
                name=payload["name"],
                provider=payload["provider"],
                description=payload["description"],
                capabilities=payload["capabilities"],
                preferred_librarian_provider=preferred_provider_id,
                preferred_librarian_model=payload["preferred_librarian_model"],
                max_librarian_agents=payload["max_librarian_agents"],
                librarian_role_prompt=payload["librarian_role_prompt"],
                librarian_role=_profile_role_value(payload["librarian_role"]),
                librarian_specialties=payload["librarian_specialties"],
                librarian_routing_priority=payload["librarian_routing_priority"],
                librarian_enabled=payload["librarian_enabled"],
                created_at=payload["created_at"],
                updated_at=payload["updated_at"],
            )
        )

    async def update_agent(
        self, agent_id: str, payload: AgentUpdatePayload
    ) -> AgentProfile:
        """Patch one agent profile from an interface payload.

        Args:
            agent_id: Target agent identifier.
            payload: Partial update payload containing changed agent fields.

        Returns:
            AgentProfile: Updated agent profile.
        """
        values = _agent_update_values(payload)
        if "preferred_librarian_provider" in values:
            await self._ensure_executable_provider(
                values["preferred_librarian_provider"]
            )
        return await self.repository.update(agent_id, AgentUpdate(values=values))

    async def delete_agent(self, agent_id: str) -> None:
        """Delete one agent profile.

        Args:
            agent_id: Target agent identifier.
        """
        await self.repository.delete(agent_id)

    async def _ensure_executable_provider(self, provider_id: str | None) -> None:
        """Reject profile assignments to non-executable providers.

        Args:
            provider_id: Preferred librarian provider id from an agent profile.

        Returns:
            None.
        """
        if provider_id is None:
            return
        provider = await self.provider_repo.get(provider_id)
        if provider is None:
            provider = await self._provider_by_name(provider_id)
        if provider is None:
            raise LibrarianResourceNotFoundError(f"Provider not found: {provider_id}")
        executable = await provider_can_execute(
            provider,
            self.secret_repo,
            self.now_provider,
        )
        if not executable:
            raise LibrarianProviderUnsupportedError(
                f"Provider is not authorized for librarian execution: {provider_id}"
            )

    async def _provider_by_name(self, provider_name: str) -> LibrarianProvider | None:
        providers = await self.provider_repo.list_all()
        for provider in providers:
            if provider.name == provider_name:
                return provider
        return None
