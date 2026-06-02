"""Context Vault persistence command contracts."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from app.memory.domain.event_enum.context_enums import (
    ContextAccessActorType,
    ContextAccessMethod,
)
from app.shared.types.extra_types import JSONObject


@dataclass(frozen=True, slots=True, kw_only=True)
class ContextChunkEmbeddingUpdate:
    """Fields required to update one context chunk embedding."""

    chunk_id: str
    embedding: str
    embedding_model: str
    embedding_dimensions: int
    embedding_provider: str
    embedding_provider_version: str
    embedding_pooling_mode: str
    embedding_normalize: bool
    embedding_fingerprint_key: str
    embedding_fingerprint: JSONObject
    embedding_indexed_at: datetime


@dataclass(frozen=True, slots=True, kw_only=True)
class ContextAccessCreate:
    """Fields required to persist one context access event."""

    context_id: str
    accessed_at: datetime
    actor_name: str
    actor_type: ContextAccessActorType
    access_method: ContextAccessMethod
    source_surface: str | None
