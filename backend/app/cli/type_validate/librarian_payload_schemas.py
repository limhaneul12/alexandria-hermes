"""Pydantic payload contracts for librarian CLI output shaping."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.shared.types.extra_types import JSONValue


class CliPayloadSchema(BaseModel):
    """Base schema for partial backend/MCP payload validation."""

    model_config = ConfigDict(
        extra="ignore",
        frozen=True,
        use_enum_values=True,
        validate_default=True,
    )


class ReviewQueueItemPayload(CliPayloadSchema):
    """Validated subset of a librarian review queue item."""

    id: JSONValue | None = None
    path: JSONValue | None = None
    reason: JSONValue | None = None
    recommended_action: JSONValue | None = None
    suggested_destination_path: JSONValue | None = None
    confidence: JSONValue | None = None
    requires_human_review: bool | None = None


class ReviewQueuePayload(CliPayloadSchema):
    """Validated subset of a librarian review queue payload."""

    total: JSONValue | None = None
    items: tuple[ReviewQueueItemPayload, ...] = Field(default_factory=tuple)

    @field_validator("items", mode="before")
    @classmethod
    def _filter_item_objects(cls, value: object) -> object:
        if isinstance(value, list):
            return [item for item in value if isinstance(item, dict)]
        return value


class McpSmokePayload(CliPayloadSchema):
    """Validated subset of an MCP smoke-check payload."""

    ok: bool = False
    mcp_url: JSONValue | None = None
    required_tools: tuple[JSONValue, ...] = Field(default_factory=tuple)
    missing_tools: tuple[JSONValue, ...] = Field(default_factory=tuple)
    tool_count: JSONValue | None = None


class RagStatusPayload(CliPayloadSchema):
    """Validated subset of librarian RAG health fields."""

    fts: JSONValue | None = None
    vector: JSONValue | None = None
    embedding: JSONValue | None = None


class CurrentCompactPayload(CliPayloadSchema):
    """Validated subset of CURRENT Memory Compact freshness fields."""

    id: JSONValue | None = None
    age_days: JSONValue | None = None
    max_age_days: JSONValue | None = None


class ReadinessReviewQueuePayload(CliPayloadSchema):
    """Validated subset of readiness review queue counts."""

    total: JSONValue | None = None
    auto_move_candidates: JSONValue | None = None
    manual_review_required: JSONValue | None = None


class NextActionPayload(CliPayloadSchema):
    """Validated subset of a recommended librarian next action."""

    code: JSONValue | None = None
    tool: JSONValue | None = None


class ReadinessPayload(CliPayloadSchema):
    """Validated subset of librarian readiness payloads."""

    ready: bool | None = None
    warnings: tuple[JSONValue, ...] = Field(default_factory=tuple)
    rag: RagStatusPayload = Field(default_factory=RagStatusPayload)
    review_queue: ReadinessReviewQueuePayload = Field(
        default_factory=ReadinessReviewQueuePayload
    )
    current_memory_compact: CurrentCompactPayload = Field(
        default_factory=CurrentCompactPayload
    )
    next_actions: tuple[NextActionPayload, ...] = Field(default_factory=tuple)

    @field_validator("next_actions", mode="before")
    @classmethod
    def _filter_next_action_objects(cls, value: object) -> object:
        if isinstance(value, list):
            return [item for item in value if isinstance(item, dict)]
        return value


class CreatedCompactPayload(CliPayloadSchema):
    """Validated subset of compact creation result fields."""

    id: JSONValue | None = None


class PreflightPayload(CliPayloadSchema):
    """Validated subset of librarian preflight/refresh payloads."""

    status: JSONValue | None = None
    refresh_required: JSONValue | None = None
    created: CreatedCompactPayload | None = None
    post_refresh_readiness: ReadinessPayload | None = None
    readiness: ReadinessPayload | None = None

    def current_readiness(self) -> ReadinessPayload:
        """Return the strongest readiness payload embedded in the response.

        Returns:
            Post-refresh readiness, direct readiness, or an empty readiness schema.
        """
        return self.post_refresh_readiness or self.readiness or ReadinessPayload()


class ApplyStatusPayload(CliPayloadSchema):
    """Validated subset of librarian apply status payloads."""

    status: str | None = None


class CombinedCheckPayload(CliPayloadSchema):
    """Validated subset of combined librarian check payloads."""

    ok: bool = False


def validate_review_queue_payload(payload: JSONValue) -> ReviewQueuePayload:
    """Validate a review queue payload.

    Args:
        payload: JSON payload returned by the backend gateway.

    Returns:
        Validated review queue payload subset.
    """
    return ReviewQueuePayload.model_validate(_object_or_empty(payload))


def validate_mcp_smoke_payload(payload: JSONValue) -> McpSmokePayload:
    """Validate an MCP smoke payload.

    Args:
        payload: JSON payload returned by MCP smoke execution.

    Returns:
        Validated MCP smoke payload subset.
    """
    return McpSmokePayload.model_validate(_object_or_empty(payload))


def validate_preflight_payload(payload: JSONValue) -> PreflightPayload:
    """Validate a librarian preflight payload.

    Args:
        payload: JSON payload returned by compact refresh/preflight execution.

    Returns:
        Validated preflight payload subset.
    """
    return PreflightPayload.model_validate(_object_or_empty(payload))


def validate_apply_status_payload(payload: JSONValue) -> ApplyStatusPayload:
    """Validate a librarian apply status payload.

    Args:
        payload: JSON payload returned by review apply execution.

    Returns:
        Validated apply status payload subset.
    """
    return ApplyStatusPayload.model_validate(_object_or_empty(payload))


def validate_combined_check_payload(payload: JSONValue) -> CombinedCheckPayload:
    """Validate a combined librarian check payload.

    Args:
        payload: JSON payload returned by combined check execution.

    Returns:
        Validated combined check payload subset.
    """
    return CombinedCheckPayload.model_validate(_object_or_empty(payload))


def _object_or_empty(payload: JSONValue) -> dict[str, Any]:
    if isinstance(payload, dict):
        return payload
    return {}


class ReviewQueueSummaryPayload(CliPayloadSchema):
    """Output schema for compact review queue summaries."""

    total: JSONValue | None = None
    auto_move_candidates: int
    manual_review_required: int
    top_item_id: JSONValue | None = None
    top_item_path: JSONValue | None = None
    top_item_reason: JSONValue | None = None
    top_item_action: JSONValue | None = None
    top_item_confidence: JSONValue | None = None
    top_item_requires_human_review: bool | None = None


class LibrarianCheckSummaryPayload(CliPayloadSchema):
    """Output schema for compact MCP plus librarian preflight summaries."""

    ok: bool
    mcp_url: JSONValue | None = None
    mcp_tool_count: JSONValue | None = None
    mcp_required_tools_count: int
    mcp_required_tools: tuple[JSONValue, ...] = Field(default_factory=tuple)
    mcp_missing_tools: tuple[JSONValue, ...] = Field(default_factory=tuple)
    preflight_status: JSONValue | None = None
    refresh_required: JSONValue | None = None
    created: bool
    created_compact_id: JSONValue | None = None
    ready: bool | None = None
    warnings: tuple[JSONValue, ...] = Field(default_factory=tuple)
    current_compact_id: JSONValue | None = None
    compact_age_days: JSONValue | None = None
    max_compact_age_days: JSONValue | None = None
    rag_fts: JSONValue | None = None
    rag_vector: JSONValue | None = None
    rag_embedding: JSONValue | None = None
    review_queue_total: JSONValue | None = None
    review_auto_move_candidates: JSONValue | None = None
    review_manual_required: JSONValue | None = None
    next_actions_count: int
    next_action: JSONValue | None = None
    next_action_tool: JSONValue | None = None


class LibrarianCheckPayload(CliPayloadSchema):
    """Output schema for full MCP plus librarian preflight checks."""

    ok: bool
    mcp_smoke: JSONValue
    preflight: JSONValue
