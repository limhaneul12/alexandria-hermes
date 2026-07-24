"""Validate Context-specific Obsidian frontmatter identity fields."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from app.memory.application.retrieval.scope_identity import validated_scope_identity
from app.memory.domain.event_enum.context_enums import (
    ContextImportance,
    ContextKind,
    ContextScope,
    ContextSourceType,
)
from app.obsidian.application.notes.obsidian_note_templates import sha256_text
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
    field_validator,
    model_validator,
)


@dataclass(frozen=True, slots=True, kw_only=True)
class ObsidianContextIdentity:
    """Validated identity fields restored from Context frontmatter."""

    scope: ContextScope
    project: str | None
    workspace_id: str | None
    agent_id: str | None
    user_id: str | None
    session_id: str | None
    visibility: ContextScope
    status: ObsidianContextLifecycleStatus
    provenance: ObsidianContextProvenance
    content_hash: str
    version: int
    supersedes_context_id: str | None
    superseded_by_context_id: str | None
    context_kind: ContextKind
    created_at: datetime | None
    updated_at: datetime | None


@dataclass(frozen=True, slots=True, kw_only=True)
class ObsidianContextProvenance:
    """Validated generalized provenance restored from Context frontmatter."""

    source_actor_id: str | None
    source_actor_type: ContextSourceType | None
    source_run_id: str | None
    external_run_id: str | None
    artifact_refs: tuple[str, ...]
    evidence_refs: tuple[str, ...]
    confidence: ContextImportance | None


class _ContextProvenanceBoundary(BaseModel):
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
        return _normalized_uppercase_text(value)

    @field_validator(
        "source_actor_id",
        "source_run_id",
        "external_run_id",
        mode="before",
    )
    @classmethod
    def normalize_optional_text(cls, value: JSONValue) -> str | None:
        return _string_or_none(value)

    @field_validator("artifact_refs", "evidence_refs", mode="before")
    @classmethod
    def normalize_reference_list(cls, value: JSONValue) -> tuple[str, ...]:
        return _reference_tuple(value)


class _ContextFrontmatterBoundary(BaseModel):
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
    provenance: _ContextProvenanceBoundary | None = None
    content_hash: str | None = None
    version: int | None = Field(default=None, ge=1)
    supersedes_context_id: str | None = None
    superseded_by_context_id: str | None = None
    context_kind: ContextKind | None = None
    kind: str | None = None
    created_at: AwareDatetime | None = None
    updated_at: AwareDatetime | None = None

    @field_validator("scope", "visibility", mode="before")
    @classmethod
    def normalize_scope(cls, value: JSONValue) -> str | None:
        """Normalize frontmatter scope spellings before enum validation.

        Args:
            value: Raw frontmatter scope value.

        Returns:
            Canonical scope text, or None when absent.
        """
        text = _string_or_none(value)
        if text is None:
            return None
        return text.upper().replace("-", "_").replace(" ", "_")

    @field_validator("status", mode="before")
    @classmethod
    def normalize_status(
        cls,
        value: JSONValue,
    ) -> str | None:
        """Normalize frontmatter lifecycle spellings before enum validation.

        Args:
            value: Raw frontmatter status value.

        Returns:
            Canonical lifecycle text, or None when absent.
        """
        text = _string_or_none(value)
        if text is None:
            return None
        return text.lower().replace("-", "_").replace(" ", "_")

    @field_validator(
        "source_actor_type",
        "confidence",
        "context_kind",
        mode="before",
    )
    @classmethod
    def normalize_uppercase_enum(cls, value: JSONValue) -> str | None:
        """Normalize generalized provenance enum values.

        Args:
            value: Raw provenance enum value.

        Returns:
            Canonical uppercase value, or None when absent.
        """
        return _normalized_uppercase_text(value)

    @field_validator("kind", mode="before")
    @classmethod
    def normalize_legacy_kind(cls, value: JSONValue) -> str | None:
        """Normalize the legacy generic kind without constraining its taxonomy.

        Args:
            value: Raw legacy kind value.

        Returns:
            Normalized uppercase text, or None.
        """
        return _normalized_uppercase_text(value)

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
        mode="before",
    )
    @classmethod
    def normalize_optional_text(cls, value: JSONValue) -> str | None:
        """Normalize null-like and blank frontmatter scalars.

        Args:
            value: Raw frontmatter scalar value.

        Returns:
            Trimmed text, or None when absent or blank.
        """
        return _string_or_none(value)

    @field_validator("artifact_refs", "evidence_refs", mode="before")
    @classmethod
    def normalize_reference_list(cls, value: JSONValue) -> tuple[str, ...]:
        """Normalize provenance reference lists without accepting mappings.

        Args:
            value: Raw provenance reference collection.

        Returns:
            Immutable normalized reference values.
        """
        return _reference_tuple(value)

    @field_validator("content_hash", mode="before")
    @classmethod
    def normalize_content_hash(cls, value: JSONValue) -> str | None:
        text = _string_or_none(value)
        if text is None:
            return None
        normalized = text.lower()
        if len(normalized) != 64 or any(
            character not in "0123456789abcdef" for character in normalized
        ):
            raise ValueError("content_hash must be a SHA-256 hex digest")
        return normalized

    @field_validator("created_at", "updated_at", mode="before")
    @classmethod
    def normalize_legacy_timestamp(cls, value: JSONValue) -> JSONValue:
        """Expand legacy date-only timestamps to an aware UTC instant.

        Args:
            value: Raw timestamp value.

        Returns:
            Aware timestamp text for date-only input, otherwise the input.
        """
        if isinstance(value, str) and len(value.strip()) == 10:
            return f"{value.strip()}T00:00:00Z"
        return value

    @model_validator(mode="after")
    def reject_conflicting_provenance_shapes(self) -> _ContextFrontmatterBoundary:
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


def context_identity_from_frontmatter(
    frontmatter: JSONObject,
    project: str | None,
    status: str,
    *,
    generated_content_hash: str,
) -> ObsidianContextIdentity:
    """Return validated Context identity restored from Obsidian frontmatter.

    Args:
        frontmatter: Parsed JSON-compatible frontmatter payload.
        project: Project value already normalized by the note indexer.
        status: Note lifecycle status already normalized by the note indexer.
        generated_content_hash: Canonical SHA-256 digest of normalized note content.

    Returns:
        Validated identity fields for Context recall.

    Raises:
        ValueError: If scope, required identity, or status is invalid.
    """
    try:
        boundary = _ContextFrontmatterBoundary.model_validate(frontmatter)
    except ValidationError as exc:
        raise ValueError(_frontmatter_validation_message(exc)) from exc

    resolved_project = boundary.project if boundary.project is not None else project
    resolved_status = _status_value(boundary.status, status)

    scope = boundary.scope
    if scope is None:
        scope = (
            ContextScope.PROJECT
            if resolved_project is not None
            else ContextScope.GLOBAL
        )

    provenance = boundary.provenance
    if (
        boundary.content_hash is not None
        and boundary.content_hash != generated_content_hash
    ):
        raise ValueError("INVALID_CONTENT_HASH: Context body hash does not match")
    identity = ObsidianContextIdentity(
        scope=scope,
        project=resolved_project,
        workspace_id=boundary.workspace_id,
        agent_id=boundary.agent_id,
        user_id=boundary.user_id,
        session_id=boundary.session_id,
        visibility=boundary.visibility or scope,
        status=resolved_status,
        provenance=ObsidianContextProvenance(
            source_actor_id=_provenance_value(
                boundary.source_actor_id, provenance, "source_actor_id"
            ),
            source_actor_type=_provenance_value(
                boundary.source_actor_type, provenance, "source_actor_type"
            ),
            source_run_id=_provenance_value(
                boundary.source_run_id, provenance, "source_run_id"
            ),
            external_run_id=_provenance_value(
                boundary.external_run_id, provenance, "external_run_id"
            ),
            artifact_refs=_provenance_value(
                boundary.artifact_refs, provenance, "artifact_refs"
            ),
            evidence_refs=_provenance_value(
                boundary.evidence_refs, provenance, "evidence_refs"
            ),
            confidence=_provenance_value(boundary.confidence, provenance, "confidence"),
        ),
        content_hash=boundary.content_hash or generated_content_hash,
        version=boundary.version or 1,
        supersedes_context_id=boundary.supersedes_context_id,
        superseded_by_context_id=boundary.superseded_by_context_id,
        context_kind=boundary.context_kind or _legacy_context_kind(boundary.kind),
        created_at=boundary.created_at,
        updated_at=boundary.updated_at,
    )
    context_id = _frontmatter_context_id(frontmatter)
    for related_context_id in (
        identity.supersedes_context_id,
        identity.superseded_by_context_id,
    ):
        if context_id is not None and related_context_id == context_id:
            raise ValueError("INVALID_SUPERSEDE: Context cannot supersede itself")
    validate_scope_identity(identity)
    return identity


def _legacy_context_kind(value: str | None) -> ContextKind:
    """Return a Context kind only when a legacy generic kind uses that enum."""
    if value is None:
        return ContextKind.MEMORY
    try:
        return ContextKind(value)
    except ValueError:
        return ContextKind.MEMORY


def normalized_context_frontmatter(
    identity: ObsidianContextIdentity,
) -> JSONObject:
    """Return canonical identity, lifecycle, and provenance frontmatter.

    Args:
        identity: Validated Context identity and metadata.

    Returns:
        Canonical frontmatter fields for Markdown persistence.
    """
    provenance = identity.provenance
    return {
        "scope": identity.scope.value,
        "project": identity.project,
        "workspace_id": identity.workspace_id,
        "agent_id": identity.agent_id,
        "user_id": identity.user_id,
        "session_id": identity.session_id,
        "visibility": identity.visibility.value,
        "status": identity.status.value,
        "source_actor_id": provenance.source_actor_id,
        "source_actor_type": (
            None
            if provenance.source_actor_type is None
            else provenance.source_actor_type.value
        ),
        "source_run_id": provenance.source_run_id,
        "external_run_id": provenance.external_run_id,
        "artifact_refs": list(provenance.artifact_refs),
        "evidence_refs": list(provenance.evidence_refs),
        "confidence": (
            None if provenance.confidence is None else provenance.confidence.value
        ),
        "content_hash": identity.content_hash,
        "version": identity.version,
        "supersedes_context_id": identity.supersedes_context_id,
        "superseded_by_context_id": identity.superseded_by_context_id,
        "context_kind": identity.context_kind.value,
        "created_at": (
            None if identity.created_at is None else identity.created_at.isoformat()
        ),
        "updated_at": (
            None if identity.updated_at is None else identity.updated_at.isoformat()
        ),
    }


def context_content_hash(content: str) -> str:
    """Return the canonical SHA-256 digest for Context Markdown body content.

    Args:
        content: Context Markdown body.

    Returns:
        Lowercase SHA-256 hexadecimal digest of normalized body content.
    """
    return sha256_text(content.strip("\n"))


def validate_scope_identity(identity: ObsidianContextIdentity) -> None:
    """Validate required identity fields for one Context scope.

    Args:
        identity: Context identity restored from frontmatter.
    """
    validated_scope_identity(
        (identity.scope,),
        identity.project,
        identity.workspace_id,
        identity.agent_id,
        identity.user_id,
        identity.session_id,
    )


def _status_value(
    frontmatter_status: ObsidianContextLifecycleStatus | None,
    note_status: str,
) -> ObsidianContextLifecycleStatus:
    if frontmatter_status is not None:
        return frontmatter_status
    try:
        return ObsidianContextLifecycleStatus.from_frontmatter_text(note_status)
    except ValueError as exc:
        raise ValueError(f"INVALID_STATUS: {note_status}") from exc


def _string_or_none(value: JSONValue) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError("frontmatter scalar must be a string")
    text = value.strip()
    if not text:
        return None
    return text


def _normalized_uppercase_text(value: JSONValue) -> str | None:
    text = _string_or_none(value)
    if text is None:
        return None
    return text.upper().replace("-", "_").replace(" ", "_")


def _reference_tuple(value: JSONValue) -> tuple[str, ...]:
    if value is None:
        return ()
    if not isinstance(value, list | tuple):
        raise ValueError("provenance references must be a string sequence")
    references: list[str] = []
    for item in value:
        if not isinstance(item, str):
            raise ValueError("provenance references must contain strings")
        text = item.strip()
        if text:
            references.append(text)
    return tuple(references)


def _provenance_value[Value](
    flat_value: Value,
    nested: _ContextProvenanceBoundary | None,
    field_name: str,
) -> Value:
    if flat_value not in (None, ()) or nested is None:
        return flat_value
    return getattr(nested, field_name)


def _frontmatter_context_id(frontmatter: JSONObject) -> str | None:
    value = frontmatter.get("id")
    if not isinstance(value, str):
        return None
    return value.strip() or None


def _frontmatter_validation_message(error: ValidationError) -> str:
    invalid_fields = {
        str(item["loc"][0]) for item in error.errors(include_url=False) if item["loc"]
    }
    if "status" in invalid_fields:
        return "INVALID_STATUS: Context frontmatter status is invalid"
    if "scope" in invalid_fields:
        return "INVALID_SCOPE: Context frontmatter scope is invalid"
    if "content_hash" in invalid_fields or "version" in invalid_fields:
        return "INVALID_CONTENT_INTEGRITY: Context hash or version is invalid"
    provenance_fields = {
        "provenance",
        "source_actor_id",
        "source_actor_type",
        "source_run_id",
        "external_run_id",
        "artifact_refs",
        "evidence_refs",
        "confidence",
    }
    if invalid_fields & provenance_fields:
        return "INVALID_PROVENANCE: Context frontmatter provenance is invalid"
    return "INVALID_SCOPE_IDENTITY: Context frontmatter identity is invalid"
