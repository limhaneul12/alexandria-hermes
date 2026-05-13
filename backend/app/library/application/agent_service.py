"""Agent profile service."""

from __future__ import annotations

from dataclasses import dataclass

from app.library.domain.entities.read_models import AgentProfile
from app.library.domain.repositories.agent_repository import AgentRepository
from app.library.domain.repositories.librarian_repository import (
    LibrarianProviderRepository,
)
from app.shared.exceptions import ValidationError
from app.shared.types.extra_types import JSONValue


@dataclass(frozen=True)
class AgentService:
    """Application service for CRUD on agent profiles."""

    repository: AgentRepository
    librarian_provider_repo: LibrarianProviderRepository

    async def list_agents(self) -> list[AgentProfile]:
        """List all agents."""
        return await self.repository.list_all()

    async def get_agent(self, agent_id: str) -> AgentProfile | None:
        """Read one agent."""
        return await self.repository.get(agent_id)

    async def create_agent(self, payload: dict[str, JSONValue]) -> AgentProfile:
        """Create one profile."""
        await self._validate_librarian_provider_assignment(payload)
        return await self.repository.create(payload)

    async def update_agent(
        self, agent_id: str, payload: dict[str, JSONValue]
    ) -> AgentProfile:
        """Patch one profile."""
        await self._validate_librarian_provider_assignment(payload)
        return await self.repository.update(agent_id, payload)

    async def delete_agent(self, agent_id: str) -> None:
        """Delete one profile."""
        await self.repository.delete(agent_id)

    async def _validate_librarian_provider_assignment(
        self,
        payload: dict[str, JSONValue],
    ) -> None:
        """Validate optional librarian provider assignment.

        Args:
            payload: Create or patch payload.

        Return:
            None.
        """
        if "preferred_librarian_provider" not in payload:
            return

        provider_id = payload["preferred_librarian_provider"]
        if provider_id is None:
            return
        if not isinstance(provider_id, str):
            raise ValidationError("Librarian provider id must be a string")

        provider = await self.librarian_provider_repo.get(provider_id)
        if provider is None:
            raise ValidationError("Librarian provider not found")
        if not provider.enabled:
            raise ValidationError("Librarian provider is disabled")
