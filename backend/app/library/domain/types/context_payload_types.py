"""Context Vault payload contracts."""

from __future__ import annotations

from datetime import datetime

from app.library.domain.event_enum.context_enums import (
    ContextContentFormat,
    ContextImportance,
    ContextKind,
    ContextSourceType,
    ContextStorageStatus,
    RagHealthState,
    RagStrategy,
)
from app.shared.types.extra_types import JSONValue
from typing_extensions import TypedDict


class ContextMetadataPayload(TypedDict, extra_items=JSONValue):
    """Arbitrary JSON metadata owned by Context Vault callers."""


class ContextLintNormalizedPayload(TypedDict, closed=True):
    """Normalized lint fields after boundary validation."""

    kind: ContextKind
    title: str
    summary: str
    project: str | None
    source_agent: str
    tags: list[str]


class ContextPayload(TypedDict, closed=True):
    """API payload for one stored context."""

    id: str
    kind: ContextKind
    title: str
    summary: str
    content: str
    content_format: ContextContentFormat
    project: str | None
    source_agent: str
    source_type: ContextSourceType
    importance: ContextImportance
    tags: list[str]
    status: ContextStorageStatus
    quality_score: int
    warnings: list[str]
    restore_prompt: str | None
    metadata: ContextMetadataPayload
    created_at: datetime
    updated_at: datetime
    last_accessed_at: datetime | None
    expires_at: datetime | None
    archived_at: datetime | None
    access_count: int
    is_archived: bool


class ContextChunkPayload(TypedDict, closed=True):
    """API payload for one stored context chunk."""

    id: str
    context_id: str
    chunk_index: int
    heading: str | None
    content: str
    token_count: int
    content_hash: str
    metadata: ContextMetadataPayload
    created_at: datetime


class ContextLintPayload(TypedDict, closed=True):
    """API payload for one Context Harness lint result."""

    ok: bool
    status: ContextStorageStatus
    score: int
    errors: list[str]
    warnings: list[str]
    suggestions: list[str]
    redacted_content: str
    normalized: ContextLintNormalizedPayload


class ContextSearchMatchPayload(TypedDict, closed=True):
    """API payload for one retrieved context match."""

    context: ContextPayload
    chunk: ContextChunkPayload
    score: float
    fts_score: float | None
    vector_score: float | None
    why_retrieved: str


class ContextPackPayload(TypedDict, closed=True):
    """API payload for one RAG Context Pack."""

    query: str
    strategy: RagStrategy
    effective_strategy: RagStrategy
    warnings: list[str]
    matches: list[ContextSearchMatchPayload]
    context_pack: str


class RagHealthPayload(TypedDict, closed=True):
    """API payload for RAG dependency health."""

    fts: RagHealthState
    vector: RagHealthState
    embedding: RagHealthState
    default_strategy: RagStrategy
    model_name: str
    dimensions: int
    warnings: list[str]
