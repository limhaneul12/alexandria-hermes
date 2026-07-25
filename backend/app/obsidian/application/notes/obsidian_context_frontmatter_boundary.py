"""Pydantic validation boundary for Context-specific Obsidian frontmatter."""

from __future__ import annotations

from app.memory.domain.event_enum.context_enums import (
    ContextImportance,
    ContextKind,
    ContextScope,
    ContextSourceType,
)
from app.obsidian.application.notes.obsidian_context_frontmatter_values import (
    frontmatter_validation_message,
    normalized_content_hash,
    normalized_legacy_timestamp,
    normalized_scope_text,
    normalized_status_text,
    normalized_uppercase_text,
    reference_tuple,
    string_or_none,
)
from app.obsidian.domain.event_enum.obsidian_enums import (
    ObsidianContextLifecycleStatus,
)
from app.shared.types.extra_types import JSONObject, JSONValue
from pydantic import (
    AwareDatetime,
    BaseModel,
    ConfigDict,
    Field,
    ValidationError,
    ValidationInfo,
    field_validator,
    model_validator,
)


class ContextProvenanceBoundary(BaseModel):
    """Boundary schema for the optional nested provenance input shape."""

    model_config = ConfigDict(extra="forbid", frozen=True, validate_default=True)

    source_actor_id: str | None = None
    source_actor_type: ContextSourceType | None = None
    source_run_id: str | None = None
    external_run_id: str | None = None
    artifact_refs: tuple[str, ...] = ()
    evidence_refs: tuple[str, ...] = ()
    confidence: ContextImportance | None = None

    @field_validator("source_actor_type", "confidence", mode="before")
    @classmethod
    def normalize_uppercase_enum(cls, value: JSONValue) -> str | None:
        """Normalize nested provenance enum values.

        Args:
            value: Raw provenance enum value.

        Returns:
            Canonical uppercase text when present.
        """
        return normalized_uppercase_text(value)

    @field_validator(
        "source_actor_id",
        "source_run_id",
        "external_run_id",
        mode="before",
    )
    @classmethod
    def normalize_optional_text(cls, value: JSONValue) -> str | None:
        """Normalize optional nested provenance text.

        Args:
            value: Raw provenance scalar value.

        Returns:
            Trimmed text when present.
        """
        return string_or_none(value)

    @field_validator(
        "artifact_refs",
        "evidence_refs",
        mode="before",
    )
    @classmethod
    def normalize_reference_list(cls, value: JSONValue) -> tuple[str, ...]:
        """Normalize nested provenance reference lists.

        Args:
            value: Raw reference collection.

        Returns:
            Immutable normalized references.
        """
        return reference_tuple(value)


class ContextFrontmatterBoundary(BaseModel):
    """Boundary schema for known Context frontmatter identity fields."""

    model_config = ConfigDict(extra="allow", frozen=True, validate_default=True)

    scope: ContextScope | None = None
    project: str | None = None
    workspace_id: str | None = None
    agent_id: str | None = None
    user_id: str | None = None
    session_id: str | None = None
    visibility: ContextScope | None = None
    status: ObsidianContextLifecycleStatus | None = None
    source_actor_id: str | None = None
    source_actor_type: ContextSourceType | None = None
    source_run_id: str | None = None
    external_run_id: str | None = None
    artifact_refs: tuple[str, ...] = ()
    evidence_refs: tuple[str, ...] = ()
    confidence: ContextImportance | None = None
    provenance: ContextProvenanceBoundary | None = None
    content_hash: str | None = None
    version: int | None = Field(default=None, ge=1)
    supersedes_context_id: str | None = None
    superseded_by_context_id: str | None = None
    context_kind: ContextKind | None = None
    kind: str | None = None
    created_at: AwareDatetime | None = None
    updated_at: AwareDatetime | None = None
    recorded_at: AwareDatetime | None = None
    observed_at: AwareDatetime | None = None
    valid_from: AwareDatetime | None = None
    valid_to: AwareDatetime | None = None
    reconciliation_candidate_id: str | None = None
    conflict_set_ids: tuple[str, ...] = ()

    @field_validator("scope", "visibility", "status", mode="before")
    @classmethod
    def normalize_scope_or_status(
        cls,
        value: JSONValue,
        info: ValidationInfo,
    ) -> str | None:
        """Normalize scope and lifecycle enum spellings.

        Args:
            value: Raw frontmatter enum value.
            info: Pydantic field validation metadata.

        Returns:
            Canonical enum text when present.
        """
        if info.field_name == "status":
            return normalized_status_text(value)
        return normalized_scope_text(value)

    @field_validator(
        "source_actor_type",
        "confidence",
        "context_kind",
        "kind",
        mode="before",
    )
    @classmethod
    def normalize_uppercase_enum(cls, value: JSONValue) -> str | None:
        """Normalize enum-like and legacy kind text to uppercase spelling.

        Args:
            value: Raw enum-like value.

        Returns:
            Canonical uppercase text when present.
        """
        return normalized_uppercase_text(value)

    @field_validator(
        "project",
        "workspace_id",
        "agent_id",
        "user_id",
        "session_id",
        "source_actor_id",
        "source_run_id",
        "external_run_id",
        "supersedes_context_id",
        "superseded_by_context_id",
        "reconciliation_candidate_id",
        "content_hash",
        mode="before",
    )
    @classmethod
    def normalize_optional_text(
        cls,
        value: JSONValue,
        info: ValidationInfo,
    ) -> str | None:
        """Normalize optional text and validate content hashes.

        Args:
            value: Raw frontmatter scalar value.
            info: Pydantic field validation metadata.

        Returns:
            Canonical optional text when present.
        """
        if info.field_name == "content_hash":
            return normalized_content_hash(value)
        return string_or_none(value)

    @field_validator(
        "artifact_refs",
        "evidence_refs",
        "conflict_set_ids",
        mode="before",
    )
    @classmethod
    def normalize_reference_list(cls, value: JSONValue) -> tuple[str, ...]:
        """Normalize provenance reference lists without accepting mappings.

        Args:
            value: Raw provenance reference collection.

        Returns:
            Immutable normalized reference values.
        """
        return reference_tuple(value)

    @field_validator(
        "created_at",
        "updated_at",
        "recorded_at",
        "observed_at",
        "valid_from",
        "valid_to",
        mode="before",
    )
    @classmethod
    def normalize_timestamp(cls, value: JSONValue) -> JSONValue:
        """Expand legacy date-only timestamps to an aware UTC instant.

        Args:
            value: Raw timestamp value.

        Returns:
            Aware timestamp text for date-only input, otherwise the input.
        """
        return normalized_legacy_timestamp(value)

    @model_validator(mode="after")
    def reject_conflicting_provenance_shapes(self) -> ContextFrontmatterBoundary:
        """Reject ambiguous flat and nested provenance values.

        Returns:
            Validated boundary model when the representations agree.
        """
        nested = self.provenance
        if nested is None:
            return self
        for field_name in (
            "source_actor_id",
            "source_actor_type",
            "source_run_id",
            "external_run_id",
            "artifact_refs",
            "evidence_refs",
            "confidence",
        ):
            flat_value = getattr(self, field_name)
            nested_value = getattr(nested, field_name)
            if flat_value not in (None, ()) and flat_value != nested_value:
                raise ValueError(
                    f"conflicting flat and nested provenance field: {field_name}"
                )
        return self


def validate_context_frontmatter(frontmatter: JSONObject) -> ContextFrontmatterBoundary:
    """Validate raw Context frontmatter and translate boundary failures.

    Args:
        frontmatter: Parsed JSON-compatible frontmatter payload.

    Returns:
        Validated Context frontmatter boundary model.

    Raises:
        ValueError: If a known Context field is invalid.
    """
    try:
        return ContextFrontmatterBoundary.model_validate(frontmatter)
    except ValidationError as exc:
        raise ValueError(frontmatter_validation_message(exc)) from exc
