"""Memory Compact read model entities."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from app.memory.domain.event_enum.memory_compact_enums import (
    MemoryCompactStatus,
)


@dataclass(frozen=True, slots=True, kw_only=True)
class MemoryCompactSourceRef:
    """Source reference attached to one Memory Compact."""

    id: str
    compact_id: str
    source_type: str
    source_id: str
    title: str
    detail_path: str


@dataclass(frozen=True, slots=True, kw_only=True)
class MemoryCompact:
    """First-class durable summary of long-term project memory."""

    id: str
    project: str | None
    covered_from: datetime
    covered_to: datetime
    markdown_body: str
    status: MemoryCompactStatus
    source_refs: tuple[MemoryCompactSourceRef, ...]
    created_at: datetime
    updated_at: datetime
    archived_at: datetime | None
