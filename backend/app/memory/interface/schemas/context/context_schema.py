"""Context Vault request and response schemas."""

from __future__ import annotations

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
from app.memory.domain.types.context_payload_types import (
    ContextLintNormalizedPayload,
)
from app.shared.schemas.common_schemas import StrictRootSchemaModel, StrictSchemaModel
from app.shared.types.extra_types import JSONObject
from pydantic import ConfigDict, Field, field_validator


class ContextLintRequest(StrictSchemaModel):
    """Payload for linting context content before persistence."""

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "kind": "HANDOFF",
                    "title": "Sprint handoff",
                    "summary": "Current implementation state.",
                    "content": "# Sprint handoff\n\n## Summary\n...",
                    "project": "alexandria-hermes",
                    "source_agent": "Hermes",
                    "tags": ["handoff"],
                }
            ]
        }
    )

    kind: ContextKind
    title: str = Field(min_length=1)
    content: str = Field(min_length=1)
    summary: str | None = None
    project: str | None = None
    scope: ContextScope = ContextScope.PROJECT
    workspace_id: str | None = None
    agent_id: str | None = None
    user_id: str | None = None
    session_id: str | None = None
    visibility: ContextScope = ContextScope.PROJECT
    source_agent: str = "Hermes"
    tags: list[str] = Field(default_factory=list)


class ContextLintResponse(StrictSchemaModel):
    """Machine-readable lint result."""

    ok: bool
    status: ContextStorageStatus
    score: int
    errors: list[str]
    warnings: list[str]
    suggestions: list[str]
    redacted_content: str
    redaction_report: list[str]
    save_suggestion: JSONObject
    normalized: ContextLintNormalizedPayload


class ContextSaveRequest(ContextLintRequest):
    """Payload for saving a context."""

    source_type: ContextSourceType = ContextSourceType.AGENT
    importance: ContextImportance = ContextImportance.MEDIUM
    expires_at: datetime | None = None
    metadata: JSONObject = Field(default_factory=dict)


class ContextCaptureRequest(ContextSaveRequest):
    """Payload for capture-semantics context saving."""


class HarnessCaptureRequest(StrictSchemaModel):
    """Payload for saving an agent-owned execution harness."""

    task_goal: str = Field(min_length=1)
    reusable_procedure: str = Field(min_length=1)
    summary: str | None = None
    project: str | None = None
    scope: ContextScope = ContextScope.PROJECT
    workspace_id: str | None = None
    agent_id: str | None = None
    user_id: str | None = None
    session_id: str | None = None
    source_agent: str = "Hermes"
    environment: str | None = None
    trigger_context: str | None = None
    steps: list[str] = Field(default_factory=list)
    commands: list[str] = Field(default_factory=list)
    tests: list[str] = Field(default_factory=list)
    failures: list[str] = Field(default_factory=list)
    fixes: list[str] = Field(default_factory=list)
    artifacts: list[str] = Field(default_factory=list)
    recall_keywords: list[str] = Field(default_factory=list)
    safety_notes: list[str] = Field(default_factory=list)
    metadata: JSONObject = Field(default_factory=dict)


class ContextPrepareCompactRequest(StrictSchemaModel):
    """Payload for generating and saving a compact context."""

    project: str | None = None
    scope: ContextScope = ContextScope.PROJECT
    workspace_id: str | None = None
    agent_id: str | None = None
    user_id: str | None = None
    session_id: str | None = None
    visibility: ContextScope = ContextScope.PROJECT
    source_agent: str = "Hermes"
    current_goal: str = Field(min_length=1)
    completed: list[str] = Field(default_factory=list)
    in_progress: list[str] = Field(default_factory=list)
    key_decisions: list[str] = Field(default_factory=list)
    next_actions: list[str] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)


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
    created_at: datetime
    updated_at: datetime
    last_accessed_at: datetime | None
    expires_at: datetime | None
    archived_at: datetime | None
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
    created_at: datetime


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
    accessed_at: datetime
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


class RagStatusResponse(StrictSchemaModel):
    """Context RAG health response."""

    fts: RagHealthState
    vector: RagHealthState
    embedding: RagHealthState
    default_strategy: RagStrategy
    model_name: str
    dimensions: int
    warnings: list[str]


class ContextReindexResponse(StrictSchemaModel):
    """Context embedding reindex response."""

    scanned: int
    updated: int
    skipped: int
    warnings: list[str]
