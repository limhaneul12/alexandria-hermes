"""Librarian read models returned by repository ports."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from app.librarian.domain.event_enum.collaboration_enums import LibrarianProfileRole


@dataclass(frozen=True, slots=True)
class AgentProfile:
    """Read model for a librarian/agent profile."""

    id: str
    name: str
    provider: str
    description: str | None
    capabilities: list[str]
    preferred_librarian_provider: str | None
    preferred_librarian_model: str | None
    max_librarian_agents: int
    librarian_role_prompt: str | None
    created_at: datetime
    updated_at: datetime
    librarian_role: LibrarianProfileRole = LibrarianProfileRole.DEFAULT_SEARCH
    librarian_specialties: list[str] | None = None
    librarian_routing_priority: int = 100
    librarian_enabled: bool = True

    def __post_init__(self) -> None:
        """Normalize persisted enum values at the read-model boundary."""
        object.__setattr__(
            self,
            "librarian_role",
            LibrarianProfileRole(self.librarian_role),
        )
