"""Read models for Obsidian-backed Alexandria notes."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from app.obsidian.domain.event_enum.obsidian_enums import (
    AlexandriaNoteType,
    ObsidianIndexStatus,
)
from app.shared.types.extra_types import JSONObject


@dataclass(frozen=True, slots=True, kw_only=True)
class ObsidianChunk:
    """Searchable chunk for one Obsidian note."""

    id: str
    note_id: str
    chunk_index: int
    heading_path: str | None
    text: str
    content_hash: str
    token_count: int


@dataclass(frozen=True, slots=True, kw_only=True)
class ObsidianNote:
    """Indexed Alexandria-managed Markdown note."""

    note_id: str
    relative_path: str
    alexandria_type: AlexandriaNoteType
    title: str
    status: str
    tags: list[str]
    project: str | None
    source: str | None
    content_hash: str
    frontmatter: JSONObject
    body: str
    index_status: ObsidianIndexStatus
    error_message: str | None
    size_bytes: int
    modified_at: datetime
    indexed_at: datetime


@dataclass(frozen=True, slots=True, kw_only=True)
class ObsidianSearchHit:
    """One Obsidian search result with path and snippet metadata."""

    note: ObsidianNote
    excerpt: str
    score: float
    chunk_id: str | None = None
    heading_path: str | None = None


@dataclass(frozen=True, slots=True, kw_only=True)
class ObsidianReindexResult:
    """Summary of one vault indexing pass."""

    files_seen: int
    files_indexed: int
    files_skipped: int
    stale_marked: int
    errors: list[str] = field(default_factory=list)


@dataclass(frozen=True, slots=True, kw_only=True)
class ObsidianVaultStatus:
    """Local Obsidian integration status."""

    vault_path: str
    alexandria_root: str
    vault_exists: bool
    alexandria_root_exists: bool
    indexed_notes: int
    stale_notes: int
    error_notes: int
