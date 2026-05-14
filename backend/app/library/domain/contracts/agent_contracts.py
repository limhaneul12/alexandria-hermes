"""Agent repository command contracts."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from app.library.domain.types.agent_payload_types import (
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
    created_at: datetime
    updated_at: datetime

    def to_record(self) -> AgentCreateRecord:
        """Return persistence fields for SQLAlchemy model construction.

        Returns:
            AgentCreateRecord: Persistence record for agent creation.
        """
        record: AgentCreateRecord = {
            "name": self.name,
            "provider": self.provider,
            "description": self.description,
            "capabilities": self.capabilities,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }
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
