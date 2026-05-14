"""Internal library read models returned by repository ports."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from app.library.domain.event_enum.item_enums import (
    CreatedByType,
    ItemStatus,
    ItemType,
    SourceType,
)
from app.library.domain.types.item_payload_types import LibraryItemPayload
from app.library.domain.types.usage_payload_types import UsageFeedbackPayload
from app.shared.types.extra_types import JSONObject


@dataclass(frozen=True, slots=True)
class AgentProfile:
    """Read model for an agent profile."""

    id: str
    name: str
    provider: str
    description: str | None
    capabilities: list[str]
    preferred_librarian_provider: str | None
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True, slots=True)
class Category:
    """Read model for a library category."""

    id: str
    name: str
    parent_id: str | None
    position: int
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True, slots=True)
class LibraryItem:
    """Read model for a unified library item."""

    id: str
    item_type: ItemType
    title: str
    summary: str | None
    content: str
    category_id: str | None
    tags: list[str]
    status: ItemStatus
    source_type: SourceType
    created_by_type: CreatedByType
    created_by_name: str
    details: JSONObject
    created_at: datetime
    updated_at: datetime
    is_archived: bool

    def to_dict(self) -> LibraryItemPayload:
        """Return the shaped API payload for this item.

        Returns:
            LibraryItemPayload: Public item payload with domain enum fields.
        """
        payload: LibraryItemPayload = {
            "id": self.id,
            "item_type": self.item_type,
            "title": self.title,
            "summary": self.summary,
            "content": self.content,
            "category_id": self.category_id,
            "tags": list(self.tags),
            "status": self.status,
            "source_type": self.source_type,
            "created_by_type": self.created_by_type,
            "created_by_name": self.created_by_name,
            "details": dict(self.details),
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }
        return payload


@dataclass(frozen=True, slots=True)
class LibrarianProvider:
    """Read model for librarian provider configuration."""

    id: str
    name: str
    provider_type: str
    auth_type: str
    enabled: bool
    config: JSONObject
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True, slots=True)
class UsageHistory:
    """Read model for a usage history event."""

    id: str
    item_id: str
    item_type: str
    agent_name: str
    librarian_provider: str | None
    query: str | None
    selection_source: str
    used_at: datetime
    success: bool
    feedback: UsageFeedbackPayload | None
