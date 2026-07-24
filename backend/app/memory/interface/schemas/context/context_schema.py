"""Context Vault request and response schemas."""

from __future__ import annotations

from app.memory.domain.event_enum.context_enums import (
    ContextAccessActorType,
    ContextAccessMethod,
    ContextContentFormat,
    ContextImportance,
    ContextKind,
    ContextRecallLifecycleStatus,
    ContextScope,
    ContextSourceType,
    ContextStorageStatus,
    RagHealthState,
    RagStrategy,
)
from app.memory.domain.types.context_payload_types import ContextRetrievalSource
from app.shared.schemas.common_schemas import StrictRootSchemaModel, StrictSchemaModel
from app.shared.schemas.datetime_schemas import AwareTimestamp
from app.shared.types.extra_types import JSONObject
from pydantic import Field, field_validator, model_validator


class ContextProvenanceResponse(StrictSchemaModel):
    """Generalized Context origin and evidence references."""

    source_actor_id: str | None
    source_actor_type: ContextSourceType | None
    source_run_id: str | None
    external_run_id: str | None
    artifact_refs: list[str]
    evidence_refs: list[str]
    confidence: ContextImportance | None


class ContextLifecycleResponse(StrictSchemaModel):
    """Context lifecycle, integrity, and supersede metadata."""

    status: ContextRecallLifecycleStatus
    content_hash: str | None
    version: int | None
    supersedes_context_id: str | None
    superseded_by_context_id: str | None


class ContextResponse(StrictSchemaModel):
    """Stored context response."""

    id: str
    canonical_context_id: str
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
    lifecycle_status: ContextRecallLifecycleStatus
    provenance: ContextProvenanceResponse
    lifecycle: ContextLifecycleResponse
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


class ContextSupersedeRequest(StrictSchemaModel):
    """Request to link one canonical Context to its replacement."""

    replacement_context_id: str = Field(min_length=1)

    @field_validator("replacement_context_id")
    @classmethod
    def normalize_replacement_context_id(cls, value: str) -> str:
        """Normalize and reject a blank replacement identifier.

        Args:
            value: Raw replacement Context identifier.

        Returns:
            Trimmed replacement Context identifier.
        """
        normalized = value.strip()
        if not normalized:
            raise ValueError("replacement_context_id must not be blank")
        return normalized


class ContextSupersedeResponse(StrictSchemaModel):
    """Bidirectional canonical Context supersede result."""

    superseded: ContextResponse
    replacement: ContextResponse


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
    include_lifecycle_statuses: list[ContextRecallLifecycleStatus] = Field(
        default_factory=list
    )

    @field_validator("include_scopes", "include_lifecycle_statuses", mode="before")
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

    @model_validator(mode="after")
    def validate_requested_scope_identities(self) -> ContextSearchRequest:
        """Reject explicit scope lanes whose required identity is absent.

        Returns:
            Validated search request.
        """
        requirements = (
            (ContextScope.PROJECT, self.project, "MISSING_PROJECT"),
            (ContextScope.AGENT, self.agent_id, "MISSING_AGENT_ID"),
            (ContextScope.USER, self.user_id, "MISSING_USER_ID"),
            (ContextScope.SESSION, self.session_id, "MISSING_SESSION_ID"),
        )
        missing = [
            field_name
            for scope, identity, field_name in requirements
            if scope in self.include_scopes
            and (identity is None or not identity.strip())
        ]
        if missing:
            raise ValueError("scope identity is required: " + ", ".join(missing))
        return self


class ContextSearchMatchResponse(StrictSchemaModel):
    """One retrieved context chunk with scores."""

    context: ContextResponse
    chunk: ContextChunkResponse
    score: float
    fts_score: float | None
    vector_score: float | None
    why_retrieved: str
    canonical_context_id: str
    lifecycle_status: ContextRecallLifecycleStatus
    source: ContextRetrievalSource
    retrieval_strategy: RagStrategy


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
