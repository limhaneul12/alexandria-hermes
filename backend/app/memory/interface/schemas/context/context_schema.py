"""Context Vault request and response schemas."""

from __future__ import annotations

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
from app.shared.schemas.common_schemas import StrictRootSchemaModel, StrictSchemaModel
from app.shared.schemas.datetime_schemas import AwareTimestamp
from app.shared.types.extra_types import JSONObject
from pydantic import Field, field_validator


class ContextResponse(StrictSchemaModel):
    """Stored context response."""

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
    metadata: JSONObject
    created_at: AwareTimestamp
    updated_at: AwareTimestamp
    last_accessed_at: AwareTimestamp | None
    expires_at: AwareTimestamp | None
    archived_at: AwareTimestamp | None
    access_count: int
    is_archived: bool


class ContextListResponse(StrictSchemaModel):
    """Paginated context list response."""

    items: list[ContextResponse]
    total: int


class ContextChunkResponse(StrictSchemaModel):
    """Stored context chunk response."""

    id: str
    context_id: str
    chunk_index: int
    heading: str | None
    content: str
    token_count: int
    content_hash: str
    metadata: JSONObject
    created_at: AwareTimestamp


class ContextChunkResponseList(StrictRootSchemaModel[list[ContextChunkResponse]]):
    """Root response schema for context chunks."""


class ContextAccessEventRequest(StrictSchemaModel):
    """Payload for recording one Context Vault access event."""

    actor_name: str = Field(default="Alexandria UI", min_length=1)
    actor_type: ContextAccessActorType = ContextAccessActorType.UI
    access_method: ContextAccessMethod = ContextAccessMethod.DETAIL_VIEW
    source_surface: str | None = "context-detail"


class ContextAccessEventResponse(StrictSchemaModel):
    """Stored context access event response."""

    id: str
    context_id: str
    accessed_at: AwareTimestamp
    actor_name: str
    actor_type: ContextAccessActorType
    access_method: ContextAccessMethod
    source_surface: str | None


class ContextAccessEventResponseList(
    StrictRootSchemaModel[list[ContextAccessEventResponse]]
):
    """Root response schema for context access event arrays."""


class ContextSearchRequest(StrictSchemaModel):
    """Payload for RAG context search."""

    query: str = Field(min_length=1)
    strategy: RagStrategy = RagStrategy.HYBRID
    limit: int = Field(default=5, ge=1, le=50)
    project: str | None = None
    kind: ContextKind | None = None
    include_scopes: list[ContextScope] = Field(default_factory=list)
    workspace_id: str | None = None
    agent_id: str | None = None
    user_id: str | None = None
    session_id: str | None = None

    @field_validator("include_scopes", mode="before")
    @classmethod
    # Broad type justified: Pydantic before validators receive raw boundary input
    # when normalizing legacy null scope filters to the default empty list.
    def default_include_scopes(cls, value: object) -> object:
        """Normalize legacy null scope filters to an empty list.

        Args:
            value: Raw boundary value.

        Returns:
            Empty list for legacy nulls, otherwise the original value for
            Pydantic to validate against the typed field contract.
        """
        if value is None:
            return []
        return value


class ContextSearchMatchResponse(StrictSchemaModel):
    """One retrieved context chunk with scores."""

    context: ContextResponse
    chunk: ContextChunkResponse
    score: float
    fts_score: float | None
    vector_score: float | None
    why_retrieved: str


class ContextPackResponse(StrictSchemaModel):
    """RAG context pack response."""

    query: str
    strategy: RagStrategy
    effective_strategy: RagStrategy
    warnings: list[str]
    recall_scopes: list[ContextScope]
    matches: list[ContextSearchMatchResponse]
    context_pack: str


class ContextEmbeddingSourceStatusResponse(StrictSchemaModel):
    """Source-level embedding fingerprint diagnostics."""

    source_name: str
    status: RagHealthState
    total_rows: int
    current_rows: int
    stale_rows: int
    missing_rows: int
    current_fingerprint: JSONObject
    stored_fingerprints: list[JSONObject]


class RagStatusResponse(StrictSchemaModel):
    """Context RAG health response."""

    fts: RagHealthState
    vector: RagHealthState
    embedding: RagHealthState
    default_strategy: RagStrategy
    model_name: str
    dimensions: int
    fingerprint: JSONObject | None
    warnings: list[str]
    source_statuses: list[ContextEmbeddingSourceStatusResponse] = Field(
        default_factory=list
    )


class ContextReindexResponse(StrictSchemaModel):
    """Context embedding reindex response."""

    scanned: int
    updated: int
    skipped: int
    warnings: list[str]


class ContextSoftRebuildResponse(StrictSchemaModel):
    """Context embedding/vector soft rebuild response."""

    mode: str
    source_preservation: str
    hard_delete_performed: bool
    before: RagStatusResponse
    source_status_before: list[ContextEmbeddingSourceStatusResponse]
    reindex: ContextReindexResponse
    after: RagStatusResponse
    source_status_after: list[ContextEmbeddingSourceStatusResponse]
    verification_query: str | None
    verification_matches: int
    verification_context_ids: list[str]
    verification_warnings: list[str]
    warnings: list[str]
