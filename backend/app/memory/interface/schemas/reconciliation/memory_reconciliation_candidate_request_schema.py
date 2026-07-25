"""Strict candidate, preview, and apply request schemas for memory reconciliation."""

from __future__ import annotations

from app.memory.domain.contracts.memory_reconciliation_contracts import (
    MemoryCandidateCreate,
    MemoryReconciliationPreviewRequest,
)
from app.memory.domain.entities.memory_reconciliation import (
    CanonicalClaim,
    CanonicalClaimQualifier,
    MemorySourceReference,
)
from app.memory.domain.event_enum.context_enums import (
    ContextScope,
)
from app.memory.domain.event_enum.reconciliation_enums import (
    MemoryClaimPolarity,
)
from app.shared.schemas.common_schemas import StrictSchemaModel
from app.shared.schemas.datetime_schemas import AwareTimestamp
from app.shared.types.types_convert_utils import enum_value
from pydantic import Field, field_validator


class CanonicalClaimQualifierRequest(StrictSchemaModel):
    """One named canonical claim qualifier."""

    name: str = Field(min_length=1, max_length=255)
    value: str = Field(min_length=1, max_length=2000)

    @field_validator("name", "value")
    @classmethod
    def normalize_text(cls, value: str) -> str:
        """Normalize required qualifier text.

        Args:
            value: Value.

        Returns:
            str: Operation result.
        """
        normalized = value.strip()
        if not normalized:
            raise ValueError("qualifier text is required")
        return normalized

    def to_entity(self) -> CanonicalClaimQualifier:
        """Convert the HTTP boundary value into an internal qualifier.

        Returns:
            CanonicalClaimQualifier: Operation result.
        """
        return CanonicalClaimQualifier(name=self.name, value=self.value)


class CanonicalClaimRequest(StrictSchemaModel):
    """Canonical proposition supplied for deterministic reconciliation."""

    subject: str = Field(min_length=1, max_length=1000)
    predicate: str = Field(min_length=1, max_length=500)
    object: str = Field(min_length=1, max_length=4000)
    qualifiers: list[CanonicalClaimQualifierRequest] = Field(default_factory=list)
    valid_from: AwareTimestamp | None = None
    valid_to: AwareTimestamp | None = None
    polarity: MemoryClaimPolarity = MemoryClaimPolarity.POSITIVE

    @field_validator("subject", "predicate", "object")
    @classmethod
    def normalize_claim_text(cls, value: str) -> str:
        """Normalize required claim text.

        Args:
            value: Value.

        Returns:
            str: Operation result.
        """
        normalized = value.strip()
        if not normalized:
            raise ValueError("canonical claim text is required")
        return normalized

    def to_entity(
        self,
        *,
        scope: ContextScope,
        project: str | None,
    ) -> CanonicalClaim:
        """Convert the request into an internal canonical claim.

        Args:
            scope: Scope.
            project: Project.

        Returns:
            CanonicalClaim: Operation result.
        """
        return CanonicalClaim(
            subject=self.subject,
            predicate=self.predicate,
            object=self.object,
            qualifiers=tuple(item.to_entity() for item in self.qualifiers),
            scope=scope,
            project=project,
            valid_from=self.valid_from,
            valid_to=self.valid_to,
            polarity=enum_value(
                self.polarity,
                MemoryClaimPolarity,
                "polarity",
            ),
        )


class MemorySourceReferenceRequest(StrictSchemaModel):
    """One explicit evidence or provenance reference."""

    source_type: str = Field(min_length=1, max_length=255)
    source_id: str = Field(min_length=1, max_length=1000)
    title: str = Field(min_length=1, max_length=2000)
    detail_path: str = Field(min_length=1, max_length=4000)
    source_hash: str | None = Field(default=None, max_length=512)
    observed_at: AwareTimestamp | None = None

    @field_validator("source_type", "source_id", "title", "detail_path")
    @classmethod
    def normalize_required_text(cls, value: str) -> str:
        """Normalize required source reference text.

        Args:
            value: Value.

        Returns:
            str: Operation result.
        """
        normalized = value.strip()
        if not normalized:
            raise ValueError("source reference text is required")
        return normalized

    def to_entity(self) -> MemorySourceReference:
        """Convert the request into an internal source reference.

        Returns:
            MemorySourceReference: Operation result.
        """
        return MemorySourceReference(
            source_type=self.source_type,
            source_id=self.source_id,
            title=self.title,
            detail_path=self.detail_path,
            source_hash=self.source_hash,
            observed_at=self.observed_at,
        )


class MemoryCandidateRequest(StrictSchemaModel):
    """Candidate memory submitted for reconciliation preview."""

    title: str = Field(min_length=1, max_length=2000)
    body: str = Field(min_length=1, max_length=500_000)
    scope: ContextScope
    project: str | None = Field(default=None, max_length=1000)
    workspace_id: str | None = Field(default=None, max_length=1000)
    agent_id: str | None = Field(default=None, max_length=1000)
    user_id: str | None = Field(default=None, max_length=1000)
    session_id: str | None = Field(default=None, max_length=1000)
    canonical_claims: list[CanonicalClaimRequest] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list, max_length=200)
    source_refs: list[MemorySourceReferenceRequest] = Field(default_factory=list)
    recorded_at: AwareTimestamp | None = None
    observed_at: AwareTimestamp | None = None
    valid_from: AwareTimestamp | None = None
    valid_to: AwareTimestamp | None = None
    requested_lifecycle: str = Field(default="active", min_length=1, max_length=64)
    candidate_id: str | None = Field(default=None, max_length=255)
    source_identity: str | None = Field(default=None, max_length=2000)

    @field_validator(
        "title",
        "body",
        "requested_lifecycle",
    )
    @classmethod
    def normalize_required_text(cls, value: str) -> str:
        """Normalize required candidate text.

        Args:
            value: Value.

        Returns:
            str: Operation result.
        """
        normalized = value.strip()
        if not normalized:
            raise ValueError("candidate text is required")
        return normalized

    @field_validator(
        "project",
        "workspace_id",
        "agent_id",
        "user_id",
        "session_id",
        "candidate_id",
        "source_identity",
    )
    @classmethod
    def normalize_optional_text(cls, value: str | None) -> str | None:
        """Normalize optional identity text.

        Args:
            value: Value.

        Returns:
            str | None: Operation result.
        """
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None

    @field_validator("tags")
    @classmethod
    def normalize_tags(cls, values: list[str]) -> list[str]:
        """Normalize and deduplicate request tags while preserving order.

        Args:
            values: Values.

        Returns:
            list[str]: Operation result.
        """
        return list(dict.fromkeys(value.strip() for value in values if value.strip()))

    def to_contract(self) -> MemoryCandidateCreate:
        """Convert the request into the application input contract.

        Returns:
            MemoryCandidateCreate: Operation result.
        """
        scope = enum_value(self.scope, ContextScope, "scope")
        return MemoryCandidateCreate(
            title=self.title,
            body=self.body,
            scope=scope,
            project=self.project,
            workspace_id=self.workspace_id,
            agent_id=self.agent_id,
            user_id=self.user_id,
            session_id=self.session_id,
            canonical_claims=tuple(
                item.to_entity(scope=scope, project=self.project)
                for item in self.canonical_claims
            ),
            tags=tuple(self.tags),
            source_refs=tuple(item.to_entity() for item in self.source_refs),
            recorded_at=self.recorded_at,
            observed_at=self.observed_at,
            valid_from=self.valid_from,
            valid_to=self.valid_to,
            requested_lifecycle=self.requested_lifecycle,
            candidate_id=self.candidate_id,
            source_identity=self.source_identity,
        )


class MemoryReconciliationPreviewHttpRequest(StrictSchemaModel):
    """Preview one memory candidate without canonical mutations."""

    candidate: MemoryCandidateRequest
    idempotency_key: str | None = Field(default=None, max_length=128)
    recall_limit: int = Field(default=20, ge=1, le=100)

    @field_validator("idempotency_key")
    @classmethod
    def normalize_idempotency_key(cls, value: str | None) -> str | None:
        """Normalize an optional caller-controlled idempotency key.

        Args:
            value: Value.

        Returns:
            str | None: Operation result.
        """
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None

    def to_contract(self) -> MemoryReconciliationPreviewRequest:
        """Convert the HTTP request into the application preview contract.

        Returns:
            MemoryReconciliationPreviewRequest: Operation result.
        """
        return MemoryReconciliationPreviewRequest(
            candidate=self.candidate.to_contract(),
            idempotency_key=self.idempotency_key,
            recall_limit=self.recall_limit,
        )


class MemoryReconciliationApplyRequest(StrictSchemaModel):
    """Apply or explicitly retry one reconciliation plan."""

    retry_failed: bool = False
