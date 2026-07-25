"""Read-only diagnostics for the memory reconciliation subsystem."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True, kw_only=True)
class MemoryReconciliationStoreDiagnostics:
    """Aggregate persistence metrics read directly from reconciliation tables."""

    reachable: bool
    total_plans: int
    pending_review_plans: int
    total_results: int
    partial_apply_results: int
    failed_results: int
    open_conflicts: int
    reviewing_conflicts: int
    temporal_state_count: int
    hard_delete_results: int
    latest_failure_code: str | None
    latest_failure_at: datetime | None


@dataclass(frozen=True, slots=True, kw_only=True)
class MemoryReconciliationDiagnostics:
    """Operational reconciliation diagnostics enriched with canonical Context count."""

    reachable: bool
    total_contexts: int
    temporal_state_count: int
    missing_temporal_states: int
    total_plans: int
    pending_review_plans: int
    total_results: int
    partial_apply_results: int
    failed_results: int
    open_conflicts: int
    reviewing_conflicts: int
    hard_delete_results: int
    latest_failure_code: str | None
    latest_failure_at: datetime | None
