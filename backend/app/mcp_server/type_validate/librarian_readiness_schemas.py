"""Pydantic contracts and policy helpers for librarian readiness tools."""

from __future__ import annotations

from datetime import UTC, datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.shared.types.extra_types import JSONObject, JSONValue


class LibrarianReadinessPayload(BaseModel):
    """Base payload schema for partial librarian readiness validation."""

    model_config = ConfigDict(
        extra="ignore",
        frozen=True,
        use_enum_values=True,
        validate_default=True,
    )


class RagStatusPayload(LibrarianReadinessPayload):
    """Validated RAG status fields used by readiness."""

    fts: str | None = None
    vector: str | None = None
    embedding: str | None = None


class CurrentCompactPayload(LibrarianReadinessPayload):
    """Validated CURRENT Memory Compact fields used by readiness."""

    id: JSONValue | None = None
    project: JSONValue | None = None
    status: JSONValue | None = None
    updated_at: str | None = None
    age_days: int | None = None
    max_age_days: int | None = None

    def calculated_age_days(self) -> int | None:
        """Calculate compact age from updated_at when possible.

        Returns:
            Non-negative age in days, or None when timestamp evidence is absent.
        """
        if self.updated_at is None:
            return None
        try:
            updated = datetime.fromisoformat(self.updated_at.replace("Z", "+00:00"))
        except ValueError:
            return None
        if updated.tzinfo is None or updated.utcoffset() is None:
            updated = updated.replace(tzinfo=UTC)
        now = datetime.now(UTC)
        return max((now - updated.astimezone(UTC)).days, 0)


class ReviewQueueItemPayload(LibrarianReadinessPayload):
    """Validated review queue item fields used by readiness."""

    suggested_destination_path: JSONValue | None = None
    requires_human_review: bool | None = None


class ReviewQueuePayload(LibrarianReadinessPayload):
    """Validated librarian review queue fields used by readiness."""

    total: int | None = None
    items: tuple[ReviewQueueItemPayload, ...] = Field(default_factory=tuple)

    @field_validator("items", mode="before")
    @classmethod
    def _filter_item_objects(cls, value: object) -> object:
        if isinstance(value, list):
            return [item for item in value if isinstance(item, dict)]
        return value

    def total_count(self) -> int:
        """Return total queue count with item count fallback.

        Returns:
            Queue total from payload or validated item count.
        """
        return self.total if self.total is not None else len(self.items)

    def auto_move_candidate_count(self) -> int:
        """Count safe auto-move candidates.

        Returns:
            Number of queue items with a destination and no manual-review flag.
        """
        return sum(
            1
            for item in self.items
            if item.suggested_destination_path
            and item.requires_human_review is not True
        )

    def manual_required_count(self) -> int:
        """Count queue items requiring human/librarian review.

        Returns:
            Number of items whose manual review flag is true.
        """
        return sum(1 for item in self.items if item.requires_human_review is True)

    def object_items(self) -> list[JSONObject]:
        """Return queue items as JSON objects for response payloads.

        Returns:
            Validated item dictionaries.
        """
        return [item.model_dump(mode="json") for item in self.items]


class NextActionPayload(LibrarianReadinessPayload):
    """Validated librarian next-action fields."""

    priority: int | None = None
    code: str | None = None
    tool: str | None = None
    summary: str | None = None
    dry_run_first: bool | None = None


class ReadinessSummaryPayload(LibrarianReadinessPayload):
    """Validated readiness summary fields used by compact refresh."""

    ready: bool | None = None
    status: str | None = None
    project: JSONValue | None = None
    rag: RagStatusPayload = Field(default_factory=RagStatusPayload)
    current_memory_compact: CurrentCompactPayload = Field(
        default_factory=CurrentCompactPayload
    )
    review_queue: ReviewQueuePayload = Field(default_factory=ReviewQueuePayload)
    warnings: tuple[str, ...] = Field(default_factory=tuple)
    next_actions: tuple[NextActionPayload, ...] = Field(default_factory=tuple)

    @field_validator("warnings", mode="before")
    @classmethod
    def _filter_warning_strings(cls, value: object) -> object:
        if isinstance(value, list):
            return [item for item in value if isinstance(item, str)]
        return value

    @field_validator("next_actions", mode="before")
    @classmethod
    def _filter_next_action_objects(cls, value: object) -> object:
        if isinstance(value, list):
            return [item for item in value if isinstance(item, dict)]
        return value


class CompactSourceRefPayload(LibrarianReadinessPayload):
    """Validated Memory Compact source reference fields."""

    source_type: str
    source_id: str
    title: str
    detail_path: str


class CompactRefreshDraftPayload(LibrarianReadinessPayload):
    """Validated compact refresh draft fields."""

    project: str | None = None
    covered_from: str
    covered_to: str
    status: str
    markdown_body: str
    source_refs: tuple[CompactSourceRefPayload, ...] = Field(default_factory=tuple)


class ReadinessReviewQueueOutputPayload(LibrarianReadinessPayload):
    """Output schema for readiness review queue summary fields."""

    total: int
    auto_move_candidates: int
    manual_review_required: int
    items: tuple[JSONObject, ...] = Field(default_factory=tuple)


class ReadinessToolOutputPayload(LibrarianReadinessPayload):
    """Output schema for the librarian readiness MCP tool."""

    ready: bool
    status: str
    project: str | None = None
    rag: RagStatusPayload
    current_memory_compact: CurrentCompactPayload
    review_queue: ReadinessReviewQueueOutputPayload
    warnings: tuple[str, ...] = Field(default_factory=tuple)
    next_actions: tuple[NextActionPayload, ...] = Field(default_factory=tuple)


class RefreshCurrentCompactOutputPayload(LibrarianReadinessPayload):
    """Output schema for the librarian compact refresh MCP tool."""

    status: str
    apply: bool
    force: bool
    refresh_required: bool
    readiness: ReadinessToolOutputPayload
    compact_draft: CompactRefreshDraftPayload
    created: JSONValue | None = None
    post_refresh_readiness: ReadinessToolOutputPayload
