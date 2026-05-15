"""Context Vault request and response schemas."""

from __future__ import annotations

from datetime import datetime

from app.library.interface.schemas._types import StrictRootSchema, StrictSchema
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
from app.memory.domain.types.context_payload_types import (
    ContextLintNormalizedPayload,
)
from app.memory.interface.schemas.context.context_enum_parsing import (
    parse_content_format_value,
    parse_context_kind_value,
    parse_importance_value,
    parse_rag_health_state_value,
    parse_rag_strategy_value,
    parse_scope_value,
    parse_source_type_value,
    parse_storage_status_value,
)
from app.shared.types.extra_types import JSONObject
from pydantic import ConfigDict, Field, field_validator


class ContextLintRequest(StrictSchema):
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

    @field_validator("kind", mode="before")
    @classmethod
    # Broad type justified: Pydantic before validators receive raw boundary input.
    def parse_kind(cls, value: object) -> ContextKind:
        """Parse JSON context kind values.

        Args:
            value: Raw boundary value.

        Returns:
            Parsed context kind.
        """
        parsed = parse_context_kind_value(value)
        if parsed is None:
            raise ValueError("kind is required")
        return parsed

    @field_validator("scope", "visibility", mode="before")
    @classmethod
    # Broad type justified: Pydantic before validators receive raw boundary input.
    def parse_scope(cls, value: object) -> ContextScope:
        """Parse JSON context scope values.

        Args:
            value: Raw boundary value.

        Returns:
            Parsed context scope.
        """
        return parse_scope_value(value)


class ContextLintResponse(StrictSchema):
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

    @field_validator("status", mode="before")
    @classmethod
    # Broad type justified: Pydantic before validators receive raw boundary input.
    def parse_status(cls, value: object) -> ContextStorageStatus:
        """Parse JSON context storage status values.

        Args:
            value: Raw boundary value.

        Returns:
            Parsed storage status.
        """
        return parse_storage_status_value(value)


class ContextSaveRequest(ContextLintRequest):
    """Payload for saving a context."""

    source_type: ContextSourceType = ContextSourceType.AGENT
    importance: ContextImportance = ContextImportance.MEDIUM
    expires_at: datetime | None = None
    metadata: JSONObject = Field(default_factory=dict)

    @field_validator("source_type", mode="before")
    @classmethod
    # Broad type justified: Pydantic before validators receive raw boundary input.
    def parse_source_type(cls, value: object) -> ContextSourceType:
        """Parse JSON context source type values.

        Args:
            value: Raw boundary value.

        Returns:
            Parsed source type.
        """
        return parse_source_type_value(value)

    @field_validator("importance", mode="before")
    @classmethod
    # Broad type justified: Pydantic before validators receive raw boundary input.
    def parse_importance(cls, value: object) -> ContextImportance:
        """Parse JSON context importance values.

        Args:
            value: Raw boundary value.

        Returns:
            Parsed importance.
        """
        return parse_importance_value(value)


class ContextCaptureRequest(ContextSaveRequest):
    """Payload for capture-semantics context saving."""


class ContextPrepareCompactRequest(StrictSchema):
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

    @field_validator("scope", "visibility", mode="before")
    @classmethod
    # Broad type justified: Pydantic before validators receive raw boundary input.
    def parse_scope(cls, value: object) -> ContextScope:
        """Parse JSON context scope values.

        Args:
            value: Raw boundary value.

        Returns:
            Parsed context scope.
        """
        return parse_scope_value(value)


class ContextResponse(StrictSchema):
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

    @field_validator("kind", mode="before")
    @classmethod
    # Broad type justified: Pydantic before validators receive raw boundary input.
    def parse_kind(cls, value: object) -> ContextKind:
        """Parse JSON context kind values.

        Args:
            value: Raw boundary value.

        Returns:
            Parsed context kind.
        """
        parsed = parse_context_kind_value(value)
        if parsed is None:
            raise ValueError("kind is required")
        return parsed

    @field_validator("content_format", mode="before")
    @classmethod
    # Broad type justified: Pydantic before validators receive raw boundary input.
    def parse_content_format(cls, value: object) -> ContextContentFormat:
        """Parse JSON context content format values.

        Args:
            value: Raw boundary value.

        Returns:
            Parsed content format.
        """
        return parse_content_format_value(value)

    @field_validator("source_type", mode="before")
    @classmethod
    # Broad type justified: Pydantic before validators receive raw boundary input.
    def parse_source_type(cls, value: object) -> ContextSourceType:
        """Parse JSON context source type values.

        Args:
            value: Raw boundary value.

        Returns:
            Parsed source type.
        """
        return parse_source_type_value(value)

    @field_validator("scope", "visibility", mode="before")
    @classmethod
    # Broad type justified: Pydantic before validators receive raw boundary input.
    def parse_scope(cls, value: object) -> ContextScope:
        """Parse JSON context scope values.

        Args:
            value: Raw boundary value.

        Returns:
            Parsed context scope.
        """
        return parse_scope_value(value)

    @field_validator("importance", mode="before")
    @classmethod
    # Broad type justified: Pydantic before validators receive raw boundary input.
    def parse_importance(cls, value: object) -> ContextImportance:
        """Parse JSON context importance values.

        Args:
            value: Raw boundary value.

        Returns:
            Parsed importance.
        """
        return parse_importance_value(value)

    @field_validator("status", mode="before")
    @classmethod
    # Broad type justified: Pydantic before validators receive raw boundary input.
    def parse_status(cls, value: object) -> ContextStorageStatus:
        """Parse JSON context storage status values.

        Args:
            value: Raw boundary value.

        Returns:
            Parsed storage status.
        """
        return parse_storage_status_value(value)


class ContextListResponse(StrictSchema):
    """Paginated context list response."""

    items: list[ContextResponse]
    total: int


class ContextChunkResponse(StrictSchema):
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


class ContextChunkResponseList(StrictRootSchema[list[ContextChunkResponse]]):
    """Root response schema for context chunks."""


class ContextSearchRequest(StrictSchema):
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

    @field_validator("strategy", mode="before")
    @classmethod
    # Broad type justified: Pydantic before validators receive raw boundary input.
    def parse_strategy(cls, value: object) -> RagStrategy:
        """Parse JSON RAG strategy values.

        Args:
            value: Raw boundary value.

        Returns:
            Parsed RAG strategy.
        """
        return parse_rag_strategy_value(value)

    @field_validator("kind", mode="before")
    @classmethod
    # Broad type justified: Pydantic before validators receive raw boundary input.
    def parse_kind(cls, value: object) -> ContextKind | None:
        """Parse optional JSON context kind values.

        Args:
            value: Raw boundary value.

        Returns:
            Parsed context kind when provided.
        """
        return parse_context_kind_value(value)

    @field_validator("include_scopes", mode="before")
    @classmethod
    # Broad type justified: Pydantic before validators receive raw boundary input.
    def parse_include_scopes(cls, value: object) -> list[ContextScope]:
        """Parse JSON context scope filter values.

        Args:
            value: Raw boundary value.

        Returns:
            Parsed context scope filters.
        """
        if value is None:
            return []
        if not isinstance(value, list):
            raise ValueError("include_scopes must be a list")
        return [parse_scope_value(item) for item in value]


class ContextSearchMatchResponse(StrictSchema):
    """One retrieved context chunk with scores."""

    context: ContextResponse
    chunk: ContextChunkResponse
    score: float
    fts_score: float | None
    vector_score: float | None
    why_retrieved: str


class ContextPackResponse(StrictSchema):
    """RAG context pack response."""

    query: str
    strategy: RagStrategy
    effective_strategy: RagStrategy
    warnings: list[str]
    recall_scopes: list[ContextScope]
    matches: list[ContextSearchMatchResponse]
    context_pack: str

    @field_validator("strategy", "effective_strategy", mode="before")
    @classmethod
    # Broad type justified: Pydantic before validators receive raw boundary input.
    def parse_strategy(cls, value: object) -> RagStrategy:
        """Parse JSON RAG strategy values.

        Args:
            value: Raw boundary value.

        Returns:
            Parsed RAG strategy.
        """
        return parse_rag_strategy_value(value)


class RagStatusResponse(StrictSchema):
    """Context RAG health response."""

    fts: RagHealthState
    vector: RagHealthState
    embedding: RagHealthState
    default_strategy: RagStrategy
    model_name: str
    dimensions: int
    warnings: list[str]

    @field_validator("fts", "vector", "embedding", mode="before")
    @classmethod
    # Broad type justified: Pydantic before validators receive raw boundary input.
    def parse_health_state(cls, value: object) -> RagHealthState:
        """Parse JSON RAG health state values.

        Args:
            value: Raw boundary value.

        Returns:
            Parsed RAG health state.
        """
        return parse_rag_health_state_value(value)

    @field_validator("default_strategy", mode="before")
    @classmethod
    # Broad type justified: Pydantic before validators receive raw boundary input.
    def parse_default_strategy(cls, value: object) -> RagStrategy:
        """Parse JSON default RAG strategy values.

        Args:
            value: Raw boundary value.

        Returns:
            Parsed default RAG strategy.
        """
        return parse_rag_strategy_value(value)
