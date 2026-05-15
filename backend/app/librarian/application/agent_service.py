"""Agent profile service."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from datetime import datetime

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
from app.shared.exceptions import NotFoundError, UnsupportedProviderError
from app.shared.types.extra_types import JSONValue
from app.shared.types.types_convert_utils import (
    now_utc,
    optional_string_value,
    required_datetime_value,
    required_string_value,
    string_items,
)

DEFAULT_MAX_LIBRARIAN_AGENTS = 1
MAX_LIBRARIAN_AGENTS_LIMIT = 6
DEFAULT_ROUTING_PRIORITY = 100


def _profile_role_value(value: JSONValue | None) -> str:
    """Normalize profile role from public input.

    Args:
        value: Interface payload value to narrow.

    Returns:
        str: Valid librarian profile role value.
    """
    if isinstance(value, str):
        return LibrarianProfileRole(value).value
    return LibrarianProfileRole.DEFAULT_SEARCH.value


def _routing_priority_value(value: JSONValue | None) -> int:
    """Normalize deterministic routing priority.

    Args:
        value: Interface payload value to narrow.

    Returns:
        int: Non-negative routing priority.
    """
    if isinstance(value, int) and not isinstance(value, bool):
        return max(value, 0)
    return DEFAULT_ROUTING_PRIORITY


def _enabled_value(value: JSONValue | None) -> bool:
    """Normalize profile enabled flag.

    Args:
        value: Interface payload value to narrow.

    Returns:
        bool: Enabled flag, defaulting to true.
    """
    if isinstance(value, bool):
        return value
    return True


def _max_librarian_agents_value(value: JSONValue | None) -> int:
    """Normalize maximum librarian agent count from an interface payload.

    Args:
        value: Interface payload value to narrow.

    Returns:
        int: Bounded positive agent count.
    """
    if isinstance(value, int) and not isinstance(value, bool):
        return min(max(value, 1), MAX_LIBRARIAN_AGENTS_LIMIT)
    return DEFAULT_MAX_LIBRARIAN_AGENTS


def _agent_update_values(payload: Mapping[str, JSONValue]) -> AgentUpdateValues:
    """Normalize public agent patch fields into an explicit update contract.

    Args:
        payload: Partial agent patch payload.

    Returns:
        AgentUpdateValues: Typed patch values accepted by the repository.
    """
    values: AgentUpdateValues = {}
    if "name" in payload:
        values["name"] = required_string_value(payload["name"], "name")
    if "provider" in payload:
        values["provider"] = required_string_value(payload["provider"], "provider")
    if "description" in payload:
        values["description"] = optional_string_value(payload["description"])
    if "capabilities" in payload:
        values["capabilities"] = string_items(payload["capabilities"])
    if "preferred_librarian_provider" in payload:
        values["preferred_librarian_provider"] = optional_string_value(
            payload["preferred_librarian_provider"]
        )
    if "preferred_librarian_model" in payload:
        values["preferred_librarian_model"] = optional_string_value(
            payload["preferred_librarian_model"]
        )
    if "max_librarian_agents" in payload:
        values["max_librarian_agents"] = _max_librarian_agents_value(
            payload["max_librarian_agents"]
        )
    if "librarian_role_prompt" in payload:
        values["librarian_role_prompt"] = optional_string_value(
            payload["librarian_role_prompt"]
        )
    if "librarian_role" in payload:
        values["librarian_role"] = _profile_role_value(payload["librarian_role"])
    if "librarian_specialties" in payload:
        values["librarian_specialties"] = string_items(payload["librarian_specialties"])
    if "librarian_routing_priority" in payload:
        values["librarian_routing_priority"] = _routing_priority_value(
            payload["librarian_routing_priority"]
        )
    if "librarian_enabled" in payload:
        values["librarian_enabled"] = _enabled_value(payload["librarian_enabled"])
    return values


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
        preferred_provider_id = optional_string_value(
            payload.get("preferred_librarian_provider")
        )
        await self._ensure_executable_provider(preferred_provider_id)
        return await self.repository.create(
            AgentCreate(
                name=required_string_value(payload.get("name"), "name"),
                provider=required_string_value(payload.get("provider"), "provider"),
                description=optional_string_value(payload.get("description")),
                capabilities=string_items(payload.get("capabilities")),
                preferred_librarian_provider=preferred_provider_id,
                preferred_librarian_model=optional_string_value(
                    payload.get("preferred_librarian_model")
                ),
                max_librarian_agents=_max_librarian_agents_value(
                    payload.get("max_librarian_agents")
                ),
                librarian_role_prompt=optional_string_value(
                    payload.get("librarian_role_prompt")
                ),
                librarian_role=_profile_role_value(payload.get("librarian_role")),
                librarian_specialties=string_items(
                    payload.get("librarian_specialties")
                ),
                librarian_routing_priority=_routing_priority_value(
                    payload.get("librarian_routing_priority")
                ),
                librarian_enabled=_enabled_value(payload.get("librarian_enabled")),
                created_at=required_datetime_value(
                    payload.get("created_at"), "created_at"
                ),
                updated_at=required_datetime_value(
                    payload.get("updated_at"), "updated_at"
                ),
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
            raise NotFoundError(f"Provider not found: {provider_id}")
        executable = await provider_can_execute(
            provider,
            self.secret_repo,
            self.now_provider,
        )
        if not executable:
            raise UnsupportedProviderError(
                f"Provider is not authorized for librarian execution: {provider_id}"
            )
