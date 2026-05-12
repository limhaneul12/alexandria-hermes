"""Agent profile service."""

from __future__ import annotations

from dataclasses import dataclass

from app.library.domain.entities.read_models import AgentProfile
from app.library.domain.repositories.agent_repository import AgentRepository
from app.shared.types.extra_types import JSONValue


@dataclass(frozen=True)
class AgentService:
    """Application service for CRUD on agent profiles."""

    repository: AgentRepository

    async def list_agents(self) -> list[AgentProfile]:
        """List all agents."""
        return await self.repository.list_all()

    async def get_agent(self, agent_id: int) -> AgentProfile | None:
        """Read one agent."""
        return await self.repository.get(agent_id)

    async def create_agent(self, payload: dict[str, JSONValue]) -> AgentProfile:
        """Create one profile."""
        return await self.repository.create(payload)

    async def update_agent(
        self, agent_id: int, payload: dict[str, JSONValue]
    ) -> AgentProfile:
        """Patch one profile."""
        return await self.repository.update(agent_id, payload)

    async def delete_agent(self, agent_id: int) -> None:
        """Delete one profile."""
        await self.repository.delete(agent_id)
