"""Strict HTTP response schemas for existing-memory reconciliation."""

from __future__ import annotations

from app.memory.domain.entities.memory_existing_reconciliation import (
    ExistingMemoryAssessment,
    ExistingMemoryReconciliationReport,
)
from app.memory.domain.event_enum.reconciliation_enums import MemoryRelationType
from app.shared.schemas.common_schemas import StrictSchemaModel


class ExistingMemoryAssessmentResponse(StrictSchemaModel):
    """One existing Context assessment exposed at the HTTP boundary."""

    context_id: str
    temporal_overlay_present: bool
    temporal_backfill_required: bool
    canonical_claim_count: int
    primary_relation: MemoryRelationType | None
    related_context_ids: list[str]
    plan_id: str | None
    plan_persisted: bool
    requires_review: bool
    warnings: list[str]

    @classmethod
    def from_entity(
        cls,
        value: ExistingMemoryAssessment,
    ) -> ExistingMemoryAssessmentResponse:
        """Map one internal assessment into a strict response model.

        Args:
            value: Value.

        Returns:
            ExistingMemoryAssessmentResponse: Operation result.
        """
        return cls(
            context_id=value.context_id,
            temporal_overlay_present=value.temporal_overlay_present,
            temporal_backfill_required=value.temporal_backfill_required,
            canonical_claim_count=value.canonical_claim_count,
            primary_relation=value.primary_relation,
            related_context_ids=list(value.related_context_ids),
            plan_id=value.plan_id,
            plan_persisted=value.plan_persisted,
            requires_review=value.requires_review,
            warnings=list(value.warnings),
        )


class ExistingMemoryReconciliationResponse(StrictSchemaModel):
    """Dry-run or apply report for one bounded existing-memory scan."""

    dry_run: bool
    scanned: int
    total_available: int
    temporal_backfill_candidates: int
    temporal_states_written: int
    plans_generated: int
    plans_persisted: int
    contexts_missing_claims: int
    review_required: int
    assessments: list[ExistingMemoryAssessmentResponse]
    warnings: list[str]
    hard_delete_performed: bool

    @classmethod
    def from_entity(
        cls,
        value: ExistingMemoryReconciliationReport,
    ) -> ExistingMemoryReconciliationResponse:
        """Map one internal scan report into a strict response model.

        Args:
            value: Value.

        Returns:
            ExistingMemoryReconciliationResponse: Operation result.
        """
        return cls(
            dry_run=value.dry_run,
            scanned=value.scanned,
            total_available=value.total_available,
            temporal_backfill_candidates=value.temporal_backfill_candidates,
            temporal_states_written=value.temporal_states_written,
            plans_generated=value.plans_generated,
            plans_persisted=value.plans_persisted,
            contexts_missing_claims=value.contexts_missing_claims,
            review_required=value.review_required,
            assessments=[
                ExistingMemoryAssessmentResponse.from_entity(item)
                for item in value.assessments
            ],
            warnings=list(value.warnings),
            hard_delete_performed=value.hard_delete_performed,
        )
