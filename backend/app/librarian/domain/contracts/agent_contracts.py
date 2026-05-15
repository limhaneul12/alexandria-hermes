"""Agent repository command contracts."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from app.librarian.domain.types.agent_payload_types import (
    AgentCreateRecord,
    AgentUpdateValues,
)


@dataclass(frozen=True, slots=True, kw_only=True)
class AgentCreate:
    """Fields required to persist an agent profile."""

    name: str
    provider: str
    description: str | None
    capabilities: list[str]
    preferred_librarian_provider: str | None
    preferred_librarian_model: str | None
    max_librarian_agents: int
    librarian_role_prompt: str | None
    librarian_role: str
    librarian_specialties: list[str]
    librarian_routing_priority: int
    librarian_enabled: bool
    created_at: datetime
    updated_at: datetime

    def to_record(self) -> AgentCreateRecord:
        """Return persistence fields for SQLAlchemy model construction.

        Returns:
            AgentCreateRecord: Persistence record for agent creation.
        """
        record = AgentCreateRecord(
            name=self.name,
            provider=self.provider,
            description=self.description,
            capabilities=self.capabilities,
            preferred_librarian_provider=self.preferred_librarian_provider,
            preferred_librarian_model=self.preferred_librarian_model,
            max_librarian_agents=self.max_librarian_agents,
            librarian_role_prompt=self.librarian_role_prompt,
            librarian_role=self.librarian_role,
            librarian_specialties=self.librarian_specialties,
            librarian_routing_priority=self.librarian_routing_priority,
            librarian_enabled=self.librarian_enabled,
            created_at=self.created_at,
            updated_at=self.updated_at,
        )
        return record


@dataclass(frozen=True, slots=True, kw_only=True)
class AgentUpdate:
    """Patch fields for an agent profile."""

    values: AgentUpdateValues

    def to_record(self) -> AgentUpdateValues:
        """Return persistence fields for patching.

        Returns:
            AgentUpdateValues: Persistence values for agent patching.
        """
        record: AgentUpdateValues = self.values.copy()
        return record
