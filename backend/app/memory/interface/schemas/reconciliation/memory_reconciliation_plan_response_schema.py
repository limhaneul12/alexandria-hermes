"""Strict plan, review queue, and result response schemas for memory reconciliation."""

from __future__ import annotations

from app.memory.domain.entities.memory_reconciliation import (
    MemoryReconciliationPlan,
    MemoryReconciliationResult,
)
from app.memory.domain.event_enum.context_enums import ContextScope
from app.memory.domain.event_enum.reconciliation_enums import (
    MemoryClaimPolarity,
    MemoryDecisionSource,
    MemoryReconciliationActionType,
    MemoryReconciliationFailureCode,
    MemoryReconciliationStatus,
    MemoryRelationType,
)
from app.shared.schemas.common_schemas import StrictSchemaModel
from app.shared.schemas.datetime_schemas import AwareTimestamp
from pydantic import TypeAdapter

_PLAN_ADAPTER = TypeAdapter(MemoryReconciliationPlan)

_RESULT_ADAPTER = TypeAdapter(MemoryReconciliationResult)


class CanonicalClaimQualifierResponse(StrictSchemaModel):
    """One normalized canonical claim qualifier."""

    name: str
    value: str


class CanonicalClaimResponse(StrictSchemaModel):
    """One normalized canonical proposition."""

    subject: str
    predicate: str
    object: str
    qualifiers: list[CanonicalClaimQualifierResponse]
    scope: ContextScope
    project: str | None
    valid_from: AwareTimestamp | None
    valid_to: AwareTimestamp | None
    polarity: MemoryClaimPolarity


class MemorySourceReferenceResponse(StrictSchemaModel):
    """One normalized evidence or provenance reference."""

    source_type: str
    source_id: str
    title: str
    detail_path: str
    source_hash: str | None
    observed_at: AwareTimestamp | None


class MemoryCandidateResponse(StrictSchemaModel):
    """Normalized memory candidate included in a reconciliation plan."""

    candidate_id: str
    title: str
    body: str
    canonical_claims: list[CanonicalClaimResponse]
    scope: ContextScope
    project: str | None
    tags: list[str]
    source_refs: list[MemorySourceReferenceResponse]
    recorded_at: AwareTimestamp
    observed_at: AwareTimestamp | None
    valid_from: AwareTimestamp | None
    valid_to: AwareTimestamp | None
    requested_lifecycle: str
    content_hash: str
    workspace_id: str | None
    agent_id: str | None
    user_id: str | None
    session_id: str | None
    source_identity: str | None


class MemoryRelationScoresResponse(StrictSchemaModel):
    """Independent scoring axes behind one relation decision."""

    semantic_similarity: float
    claim_overlap: float
    scope_compatibility: float
    temporal_compatibility: float
    source_independence: float
    polarity_conflict: float
    specificity_change: float
    freshness: float


class MemoryRelationDecisionResponse(StrictSchemaModel):
    """Explainable relation decision against one existing Context."""

    candidate_id: str
    existing_context_id: str
    relation: MemoryRelationType
    confidence: float
    reason: str
    evidence_refs: list[MemorySourceReferenceResponse]
    claim_matches: list[str]
    scores: MemoryRelationScoresResponse
    decision_source: MemoryDecisionSource
    policy_version: str
    created_at: AwareTimestamp


class MemoryReconciliationActionResponse(StrictSchemaModel):
    """One explicit action in an immutable reconciliation plan."""

    action_type: MemoryReconciliationActionType
    target_context_id: str | None
    relation: MemoryRelationType | None
    reason: str


class MemoryReconciliationPlanResponse(StrictSchemaModel):
    """Complete non-mutating reconciliation preview plan."""

    plan_id: str
    candidate: MemoryCandidateResponse
    decisions: list[MemoryRelationDecisionResponse]
    primary_decision: MemoryRelationType
    actions: list[MemoryReconciliationActionResponse]
    warnings: list[str]
    conflicting_context_ids: list[str]
    requires_review: bool
    idempotency_key: str
    status: MemoryReconciliationStatus
    created_at: AwareTimestamp

    @classmethod
    def from_entity(
        cls,
        value: MemoryReconciliationPlan,
    ) -> MemoryReconciliationPlanResponse:
        """Validate one internal plan as a strict HTTP response.

        Args:
            value: Value.

        Returns:
            MemoryReconciliationPlanResponse: Operation result.
        """
        return cls.model_validate(_PLAN_ADAPTER.dump_python(value, mode="python"))


class MemoryReviewQueueResponse(StrictSchemaModel):
    """Durable review-required reconciliation plans."""

    items: list[MemoryReconciliationPlanResponse]
    total: int

    @classmethod
    def from_entities(
        cls,
        values: list[MemoryReconciliationPlan],
    ) -> MemoryReviewQueueResponse:
        """Map persisted review-required plans into one queue response.

        Args:
            values: Values.

        Returns:
            MemoryReviewQueueResponse: Operation result.
        """
        items = [
            MemoryReconciliationPlanResponse.from_entity(value) for value in values
        ]
        return cls(items=items, total=len(items))


class MemoryReconciliationResultResponse(StrictSchemaModel):
    """Auditable result of applying one reconciliation plan."""

    reconciliation_id: str
    plan_id: str
    status: MemoryReconciliationStatus
    created_context_ids: list[str]
    updated_context_ids: list[str]
    superseded_context_ids: list[str]
    created_relation_ids: list[str]
    created_conflict_set_ids: list[str]
    merged_evidence: list[MemorySourceReferenceResponse]
    review_queue_item_ids: list[str]
    warnings: list[str]
    hard_delete_performed: bool
    failure_code: MemoryReconciliationFailureCode | None
    completed_at: AwareTimestamp | None

    @classmethod
    def from_entity(
        cls,
        value: MemoryReconciliationResult,
    ) -> MemoryReconciliationResultResponse:
        """Validate one internal result as a strict HTTP response.

        Args:
            value: Value.

        Returns:
            MemoryReconciliationResultResponse: Operation result.
        """
        return cls.model_validate(_RESULT_ADAPTER.dump_python(value, mode="python"))
