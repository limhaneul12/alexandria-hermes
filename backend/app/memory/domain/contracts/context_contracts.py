"""Context Vault persistence command contracts."""

from __future__ import annotations

from dataclasses import dataclass
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
)
from app.memory.domain.types.context_payload_types import ContextMetadataPayload


@dataclass(frozen=True, slots=True, kw_only=True)
class ContextCreate:
    """Fields required to persist a context."""

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
    expires_at: datetime | None


@dataclass(frozen=True, slots=True, kw_only=True)
class ContextChunkCreate:
    """Fields required to persist one context chunk."""

    chunk_index: int
    heading: str | None
    content: str
    token_count: int
    content_hash: str
    chunk_metadata: ContextMetadataPayload
    embedding: str | None
    embedding_model: str | None
    embedding_dimensions: int | None
    created_at: datetime


@dataclass(frozen=True, slots=True, kw_only=True)
class ContextChunkEmbeddingUpdate:
    """Fields required to update one context chunk embedding."""

    chunk_id: str
    embedding: str
    embedding_model: str
    embedding_dimensions: int


@dataclass(frozen=True, slots=True, kw_only=True)
class ContextAccessCreate:
    """Fields required to persist one context access event."""

    context_id: str
    accessed_at: datetime
    actor_name: str
    actor_type: ContextAccessActorType
    access_method: ContextAccessMethod
    source_surface: str | None
