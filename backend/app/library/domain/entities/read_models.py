"""Internal library read models returned by repository ports."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from app.shared.types.extra_types import JSONValue


@dataclass(frozen=True, slots=True)
class AgentProfile:
    """Read model for an agent profile."""

    id: int
    name: str
    provider: str
    description: str | None
    capabilities: list[str]
    preferred_librarian_provider: int | None
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True, slots=True)
class Category:
    """Read model for a library category."""

    id: int
    name: str
    parent_id: int | None
    position: int
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True, slots=True)
class LibraryItem:
    """Read model for a unified library item."""

    id: int
    item_type: str
    title: str
    summary: str | None
    content: str
    category_id: int | None
    tags: list[str]
    status: str
    source_type: str
    created_by_type: str
    created_by_name: str
    details: dict[str, JSONValue]
    created_at: datetime
    updated_at: datetime
    is_archived: bool


@dataclass(frozen=True, slots=True)
class LibrarianProvider:
    """Read model for librarian provider configuration."""

    id: int
    name: str
    provider_type: str
    auth_type: str
    enabled: bool
    config: dict[str, JSONValue]
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True, slots=True)
class UsageHistory:
    """Read model for a usage history event."""

    id: int
    item_id: int
    item_type: str
    agent_name: str
    librarian_provider: str | None
    query: str | None
    selection_source: str
    used_at: datetime
    success: bool
    feedback: dict[str, JSONValue] | None
