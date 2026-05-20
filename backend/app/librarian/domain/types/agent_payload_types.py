"""Agent domain payload contracts."""

from __future__ import annotations

from datetime import datetime

from app.librarian.domain.event_enum.collaboration_enums import LibrarianProfileRole
from typing_extensions import TypedDict


class AgentCreatePayload(TypedDict, closed=True):
    """Application payload for creating an agent profile from an I/O schema."""

    name: str
    provider: str
    description: str | None
    capabilities: list[str]
    preferred_librarian_provider: str | None
    preferred_librarian_model: str | None
    max_librarian_agents: int
    librarian_role_prompt: str | None
    librarian_role: LibrarianProfileRole | str
    librarian_specialties: list[str]
    librarian_routing_priority: int
    librarian_enabled: bool
    created_at: datetime
    updated_at: datetime


class AgentUpdatePayload(TypedDict, total=False, closed=True):
    """Application payload for patching an agent profile from an I/O schema."""

    name: str
    provider: str
    description: str | None
    capabilities: list[str]
    preferred_librarian_provider: str | None
    preferred_librarian_model: str | None
    max_librarian_agents: int
    librarian_role_prompt: str | None
    librarian_role: LibrarianProfileRole | str
    librarian_specialties: list[str]
    librarian_routing_priority: int
    librarian_enabled: bool


class AgentCreateRecord(TypedDict, closed=True):
    """Persistence record for creating an agent profile."""

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


class AgentUpdateValues(TypedDict, total=False, closed=True):
    """Patch values for an agent profile."""

    name: str
    provider: str
    description: str | None
    capabilities: list[str]
    preferred_librarian_provider: str | None
    preferred_librarian_model: str | None
    max_librarian_agents: int
    librarian_role_prompt: str | None
    librarian_role: LibrarianProfileRole
    librarian_specialties: list[str]
    librarian_routing_priority: int
    librarian_enabled: bool


class AgentUpdateRecord(TypedDict, total=False, closed=True):
    """Persistence patch values for an agent profile."""

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
