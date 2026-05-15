"""Context Vault read models."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from app.memory.domain.event_enum.context_enums import (
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
