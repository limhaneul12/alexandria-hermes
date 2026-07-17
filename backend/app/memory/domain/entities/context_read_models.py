"""Context Vault read models."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from app.memory.domain.event_enum.context_enums import (
    ContextAccessActorType,
    ContextAccessMethod,
    ContextContentFormat,
    ContextImportance,
    ContextKind,
    ContextScope,
    ContextSourceType,
    ContextStorageStatus,
    RagHealthState,
    RagStrategy,
)
from app.memory.domain.types.context_payload_types import ContextMetadataPayload
from app.shared.types.extra_types import JSONObject


@dataclass(frozen=True, slots=True)
class ContextRecord:
    """Read model for one stored context."""

    id: str
    kind: ContextKind
    title: str
    summary: str
    content: str
    content_format: ContextContentFormat
    project: str | None
    scope: ContextScope
    workspace_id: str | None
    agent_id: str | None
    user_id: str | None
    session_id: str | None
    visibility: ContextScope
    source_agent: str
    source_type: ContextSourceType
    importance: ContextImportance
    tags: list[str]
    status: ContextStorageStatus
    quality_score: int
    warnings: list[str]
    restore_prompt: str | None
    context_metadata: ContextMetadataPayload
    created_at: datetime
    updated_at: datetime
    last_accessed_at: datetime | None
    expires_at: datetime | None
    archived_at: datetime | None
    access_count: int
    is_archived: bool


@dataclass(frozen=True, slots=True)
class ContextChunkRecord:
    """Read model for one context chunk."""

    id: str
    context_id: str
    chunk_index: int
    heading: str | None
    content: str
    token_count: int
    content_hash: str
    chunk_metadata: ContextMetadataPayload
    created_at: datetime


@dataclass(frozen=True, slots=True)
class ContextAccessEventRecord:
    """Read model for one Context Vault access event."""

    id: str
    context_id: str
    accessed_at: datetime
    actor_name: str
    actor_type: ContextAccessActorType
    access_method: ContextAccessMethod
    source_surface: str | None


@dataclass(frozen=True, slots=True)
class ContextSearchMatch:
    """One retrieved chunk with its parent context."""

    context: ContextRecord
    chunk: ContextChunkRecord
    score: float
    fts_score: float | None
    vector_score: float | None
    why_retrieved: str


@dataclass(frozen=True, slots=True)
class RagDependencyHealth:
    """Health state for context RAG dependencies."""

    fts: RagHealthState
    vector: RagHealthState
    embedding: RagHealthState
    default_strategy: RagStrategy
    model_name: str
    dimensions: int
    fingerprint: JSONObject | None
    warnings: list[str]
    source_statuses: list[ContextEmbeddingSourceStatus] = field(default_factory=list)


@dataclass(frozen=True, slots=True)
class ContextEmbeddingSourceStatus:
    """Embedding fingerprint status for one configured retrieval source."""

    source_name: str
    status: RagHealthState
    total_rows: int
    current_rows: int
    stale_rows: int
    missing_rows: int
    current_fingerprint: JSONObject
    stored_fingerprints: list[JSONObject]


@dataclass(frozen=True, slots=True)
class ContextReindexResult:
    """Result for a context embedding reindex operation."""

    scanned: int
    updated: int
    skipped: int
    warnings: list[str]


@dataclass(frozen=True, slots=True)
class ContextSoftRebuildResult:
    """Operator-facing result for a soft embedding/vector rebuild."""

    mode: str
    source_preservation: str
    hard_delete_performed: bool
    before: RagDependencyHealth
    source_status_before: list[ContextEmbeddingSourceStatus]
    reindex: ContextReindexResult
    after: RagDependencyHealth
    source_status_after: list[ContextEmbeddingSourceStatus]
    verification_query: str | None
    verification_matches: int
    verification_context_ids: list[str]
    verification_warnings: list[str]
    warnings: list[str]


@dataclass(frozen=True, slots=True)
class ContextPack:
    """Agent-facing RAG context pack."""

    query: str
    strategy: RagStrategy
    effective_strategy: RagStrategy
    warnings: list[str]
    recall_scopes: list[ContextScope]
    matches: list[ContextSearchMatch]
    context_pack: str
