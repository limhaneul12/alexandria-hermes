"""Agent profile repository abstraction."""

from __future__ import annotations

from abc import ABC, abstractmethod

from app.library.domain.entities.read_models import AgentProfile
from app.shared.types.extra_types import JSONValue


class AgentRepository(ABC):
    """Persistence contract for agent profile operations."""

    @abstractmethod
    async def create(self, payload: dict[str, JSONValue]) -> AgentProfile:
        """Create an agent profile."""

    @abstractmethod
    async def get(self, agent_id: int) -> AgentProfile | None:
        """Get one agent profile."""

    @abstractmethod
    async def list_all(self) -> list[AgentProfile]:
        """List all agent profiles."""

    @abstractmethod
    async def update(
        self, agent_id: int, payload: dict[str, JSONValue]
    ) -> AgentProfile:
        """Patch profile data."""

    @abstractmethod
    async def delete(self, agent_id: int) -> None:
        """Delete one profile."""
