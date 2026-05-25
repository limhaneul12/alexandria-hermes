"""Application contracts for Obsidian vault operations."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from app.obsidian.domain.event_enum.obsidian_enums import (
    AlexandriaNoteType,
    ObsidianEdgeSourceKind,
    ObsidianRelationType,
)
from app.shared.types.extra_types import JSONObject


@dataclass(frozen=True, slots=True, kw_only=True)
class ObsidianChunkIndex:
    """Chunk data to store in the search cache."""

    chunk_index: int
    heading_path: str | None
    text: str
    content_hash: str
    token_count: int


@dataclass(frozen=True, slots=True, kw_only=True)
class ObsidianEdgeIndex:
    """Graph edge discovered while indexing one Obsidian note."""

    edge_id: str
    source_note_id: str
    source_path: str
    target_note_id: str | None
    target_path: str
    relation: ObsidianRelationType
    confidence: float
    source_kind: ObsidianEdgeSourceKind


@dataclass(frozen=True, slots=True, kw_only=True)
class ObsidianNoteIndex:
    """Normalized note data discovered during vault indexing."""

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
    size_bytes: int
    modified_at: datetime
    chunks: list[ObsidianChunkIndex]
    edges: list[ObsidianEdgeIndex] = field(default_factory=list)


@dataclass(frozen=True, slots=True, kw_only=True)
class ObsidianSearchQuery:
    """Search parameters for Obsidian note retrieval."""

    query: str
    limit: int = 10
    alexandria_type: AlexandriaNoteType | None = None
    project: str | None = None
    tags: list[str] = field(default_factory=list)


@dataclass(frozen=True, slots=True, kw_only=True)
class ObsidianSaveNote:
    """Payload for creating or replacing one managed Markdown note."""

    title: str
    body: str
    alexandria_type: AlexandriaNoteType
    note_id: str | None = None
    relative_path: str | None = None
    tags: list[str] = field(default_factory=list)
    status: str = "active"
    project: str | None = None
    source: str = "mcp"
    frontmatter: JSONObject = field(default_factory=dict)


@dataclass(frozen=True, slots=True, kw_only=True)
class ObsidianLibrarianAsk:
    """Obsidian-side librarian ask payload."""

    query: str
    active_note_path: str | None = None
    selection: str | None = None
    project: str | None = None
    preferred_alexandria_types: list[AlexandriaNoteType] = field(default_factory=list)
    save_transcript: bool = False
    delegate_to_librarian: bool = False
    provider_id: str | None = None
    profile_id: str | None = None


@dataclass(frozen=True, slots=True, kw_only=True)
class ObsidianLibrarianWorkflowStart:
    """Start request for a resumable Obsidian librarian workflow."""

    ask: ObsidianLibrarianAsk


@dataclass(frozen=True, slots=True, kw_only=True)
class ObsidianLibrarianWorkflowResume:
    """Resume request with approved workflow action ids."""

    thread_id: str
    approved_actions: list[str] = field(default_factory=list)
