"""Agent profile service."""

from __future__ import annotations

from collections.abc import Mapping

from app.library.domain.contracts.agent_contracts import AgentCreate, AgentUpdate
from app.library.domain.entities.read_models import AgentProfile
from app.library.domain.repositories.agent_repository import IAgentRepository
from app.library.domain.types.agent_payload_types import AgentUpdateValues
from app.shared.types.extra_types import JSONValue
from app.shared.types.types_convert_utils import (
    optional_string_value,
    required_datetime_value,
    required_string_value,
    string_items,
)


def _agent_update_values(payload: Mapping[str, JSONValue]) -> AgentUpdateValues:
    """Normalize public agent patch fields into an explicit update contract.

    Args:
        payload: Partial agent patch payload.

    Returns:
        AgentUpdateValues: Typed patch values accepted by the repository.
    """
    values: AgentUpdateValues = {}
    if "description" in payload:
        values["description"] = optional_string_value(payload["description"])
    if "capabilities" in payload:
        values["capabilities"] = string_items(payload["capabilities"])
    return values


class AgentService:
    """Application service for CRUD on agent profiles."""

    def __init__(
        self,
        repository: IAgentRepository,
    ) -> None:
        """Initialize agent service dependencies.

        Args:
            repository: Agent persistence repository.
        """
        self.repository = repository

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

    async def create_agent(self, payload: dict[str, JSONValue]) -> AgentProfile:
        """Create one agent profile from an interface payload.

        Args:
            payload: Validated interface payload containing agent creation fields.

        Returns:
            AgentProfile: Persisted agent profile.
        """
        return await self.repository.create(
            AgentCreate(
                name=required_string_value(payload.get("name"), "name"),
                provider=required_string_value(payload.get("provider"), "provider"),
                description=optional_string_value(payload.get("description")),
                capabilities=string_items(payload.get("capabilities")),
                created_at=required_datetime_value(
                    payload.get("created_at"), "created_at"
                ),
                updated_at=required_datetime_value(
                    payload.get("updated_at"), "updated_at"
                ),
            )
        )

    async def update_agent(
        self, agent_id: str, payload: dict[str, JSONValue]
    ) -> AgentProfile:
        """Patch one agent profile from an interface payload.

        Args:
            agent_id: Target agent identifier.
            payload: Partial update payload containing changed agent fields.

        Returns:
            AgentProfile: Updated agent profile.
        """
        values = _agent_update_values(payload)
        return await self.repository.update(agent_id, AgentUpdate(values=values))

    async def delete_agent(self, agent_id: str) -> None:
        """Delete one agent profile.

        Args:
            agent_id: Target agent identifier.
        """
        await self.repository.delete(agent_id)
