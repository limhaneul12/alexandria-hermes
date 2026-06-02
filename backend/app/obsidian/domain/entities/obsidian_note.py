"""Read models for Obsidian-backed Alexandria notes."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from app.obsidian.domain.event_enum.obsidian_enums import (
    AlexandriaNoteType,
    ObsidianEdgeSourceKind,
    ObsidianIndexStatus,
    ObsidianLibrarianJobStatus,
    ObsidianLibrarianWorkflowStatus,
    ObsidianRelationType,
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
class ObsidianEdge:
    """Indexed graph edge between Obsidian notes."""

    edge_id: str
    source_note_id: str
    source_path: str
    target_note_id: str | None
    target_path: str
    relation: ObsidianRelationType
    confidence: float
    source_kind: ObsidianEdgeSourceKind
    created_at: datetime
    indexed_at: datetime


@dataclass(frozen=True, slots=True, kw_only=True)
class ObsidianRelatedNote:
    """Related note result ranked by graph edge evidence."""

    note: ObsidianNote
    relation: ObsidianRelationType
    source_kind: ObsidianEdgeSourceKind
    direction: str
    score: float
    edge_id: str


@dataclass(frozen=True, slots=True, kw_only=True)
class ObsidianLibrarianWorkflow:
    """Persisted Obsidian librarian workflow checkpoint."""

    thread_id: str
    status: ObsidianLibrarianWorkflowStatus
    query: str
    active_note_path: str | None
    project: str | None
    provider_id: str | None
    profile_id: str | None
    delegate_requested: bool
    state: JSONObject
    created_at: datetime
    updated_at: datetime


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


@dataclass(frozen=True, slots=True, kw_only=True)
class ObsidianVaultInventoryItem:
    """One managed Markdown note discovered by vault inventory."""

    note_id: str
    relative_path: str
    alexandria_type: AlexandriaNoteType
    title: str
    status: str
    tags: list[str]
    project: str | None
    size_bytes: int
    modified_at: datetime


@dataclass(frozen=True, slots=True, kw_only=True)
class ObsidianVaultMoveCandidate:
    """One planned vault move after safety validation."""

    source_path: str
    destination_path: str
    reason: str


@dataclass(frozen=True, slots=True, kw_only=True)
class ObsidianVaultMoveSkip:
    """One skipped vault move with the safety reason."""

    source_path: str
    destination_path: str
    reason: str


@dataclass(frozen=True, slots=True, kw_only=True)
class ObsidianVaultMovePlan:
    """Dry-run move plan for a librarian vault operation."""

    status: str
    hard_delete_performed: bool
    moves: list[ObsidianVaultMoveCandidate]
    skipped: list[ObsidianVaultMoveSkip]
    ambiguous: list[ObsidianVaultMoveSkip]


@dataclass(frozen=True, slots=True, kw_only=True)
class ObsidianVaultMoveApplied:
    """One move that was safely applied."""

    source_path: str
    destination_path: str
    reason: str


@dataclass(frozen=True, slots=True, kw_only=True)
class ObsidianVaultMoveVerification:
    """Verification summary after applying a vault move plan."""

    source_root_loose_notes_remaining: int
    reindex_status: str
    verification_hits: int


@dataclass(frozen=True, slots=True, kw_only=True)
class ObsidianVaultMoveReport:
    """Final report for a safe librarian vault move operation."""

    status: str
    hard_delete_performed: bool
    moved: list[ObsidianVaultMoveApplied]
    skipped: list[ObsidianVaultMoveSkip]
    ambiguous: list[ObsidianVaultMoveSkip]
    verification: ObsidianVaultMoveVerification
    report_markdown_path: str
    report_json_path: str


@dataclass(frozen=True, slots=True, kw_only=True)
class ObsidianLibrarianJob:
    """Typed status snapshot for one librarian execution job."""

    job_id: str
    status: ObsidianLibrarianJobStatus
    operation: str
    report: ObsidianVaultMoveReport | None
    error_message: str | None
    created_at: datetime
    updated_at: datetime
