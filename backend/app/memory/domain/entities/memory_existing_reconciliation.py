"""Read models for existing-memory reconciliation and temporal backfill."""

from __future__ import annotations

from dataclasses import dataclass

from app.memory.domain.event_enum.reconciliation_enums import MemoryRelationType


@dataclass(frozen=True, slots=True, kw_only=True)
class ExistingMemoryAssessment:
    """One existing Context assessment produced by a reconciliation scan."""

    context_id: str
    temporal_overlay_present: bool
    temporal_backfill_required: bool
    canonical_claim_count: int
    primary_relation: MemoryRelationType | None
    related_context_ids: tuple[str, ...]
    plan_id: str | None
    plan_persisted: bool
    requires_review: bool
    warnings: tuple[str, ...]


@dataclass(frozen=True, slots=True, kw_only=True)
class ExistingMemoryReconciliationReport:
    """Dry-run or apply report for a bounded existing-memory scan."""

    dry_run: bool
    scanned: int
    total_available: int
    temporal_backfill_candidates: int
    temporal_states_written: int
    plans_generated: int
    plans_persisted: int
    contexts_missing_claims: int
    review_required: int
    assessments: tuple[ExistingMemoryAssessment, ...]
    warnings: tuple[str, ...]
    hard_delete_performed: bool = False
