"""Agent domain payload contracts."""

from __future__ import annotations

from datetime import datetime

from typing_extensions import TypedDict


class AgentCreateRecord(TypedDict, closed=True):
    """Persistence record for creating an agent profile."""

    name: str
    provider: str
    description: str | None
    capabilities: list[str]
    created_at: datetime
    updated_at: datetime


class AgentUpdateValues(TypedDict, total=False, closed=True):
    """Patch values for an agent profile."""

    description: str | None
    capabilities: list[str]


type AgentUpdateRecord = AgentUpdateValues
