"""Blocker, status, step, diagnosis, and next-action policy for recovery plans."""

from __future__ import annotations

from datetime import UTC, datetime
from hashlib import sha256

from app.operations.application.recovery_plan_source_policy import (
    _quarantine_artifacts,
)
from app.operations.domain.entities.operational_readiness import (
    OperationalReadinessSnapshot,
)
from app.operations.domain.entities.recovery_plan import (
    RecoveryPlanStep,
    RecoverySourceSnapshot,
)
from app.operations.domain.event_enum.operational_readiness_enums import (
    OperationalReadinessStatus,
)


def _default_idempotency_key(
    *, database_path: str | None, trigger: str, actor: str
) -> str:
    seed = f"{database_path or 'non-sqlite'}:{trigger}:{actor}"
    return sha256(seed.encode("utf-8")).hexdigest()[:24]


def _blocked_reasons(
    readiness: OperationalReadinessSnapshot,
    source_snapshot: RecoverySourceSnapshot,
    database_path: str | None,
) -> list[str]:
    reasons: list[str] = []
    if database_path is None:
        reasons.append("sqlite_database_path_unavailable")
    if source_snapshot.access_error is not None:
        reasons.append(source_snapshot.access_error)
    if not readiness.vault.exists:
        reasons.append("vault_not_found")
    if not readiness.vault.alexandria_root_exists:
        reasons.append("alexandria_root_not_found")
    if source_snapshot.managed_markdown_count == 0:
        reasons.append("managed_markdown_not_found")
    if source_snapshot.disk_free_bytes is not None and database_path is not None:
        existing_size = sum(
            artifact.size_bytes or 0
            for artifact in _quarantine_artifacts(
                database_path=database_path,
                run_id="space-check",
                created_at=datetime.now(UTC),
            )
        )
        if source_snapshot.disk_free_bytes < max(existing_size * 2, 1):
            reasons.append("insufficient_disk_space")
    return reasons


def _plan_status(
    readiness: OperationalReadinessSnapshot,
    blocked_reasons: list[str],
) -> OperationalReadinessStatus:
    if blocked_reasons:
        return OperationalReadinessStatus.BLOCKED
    if readiness.status is OperationalReadinessStatus.RECOVERY_REQUIRED:
        return OperationalReadinessStatus.RECOVERY_REQUIRED
    return readiness.status


def _diagnosis(readiness: OperationalReadinessSnapshot) -> list[str]:
    if readiness.database.corruption_detected:
        return ["SQLITE_CORRUPTION_DETECTED"]
    return list(readiness.warnings)


def _steps(readiness: OperationalReadinessSnapshot) -> list[RecoveryPlanStep]:
    if _reconciliation_only_issue(list(readiness.warnings)):
        return [
            RecoveryPlanStep(
                "inspect_memory_reconciliation",
                "Inspect reconciliation diagnostics without rebuilding storage",
                False,
            )
        ]
    return [
        RecoveryPlanStep("snapshot_sources", "Snapshot source vault metadata", False),
        RecoveryPlanStep("dispose_connections", "Dispose database connections", True),
        RecoveryPlanStep(
            "quarantine_sqlite_files", "Move SQLite files to quarantine", True
        ),
        RecoveryPlanStep(
            "rebuild_database_schema", "Rebuild migration-managed schema", True
        ),
        RecoveryPlanStep("reindex_vault", "Rebuild Obsidian index cache", True),
        RecoveryPlanStep("reindex_embeddings", "Rebuild retrieval embeddings", True),
        RecoveryPlanStep("verify_readiness", "Verify operational readiness", False),
    ]


def _next_actions(
    status: OperationalReadinessStatus,
    blocked_reasons: list[str],
    warnings: list[str],
) -> list[str]:
    if blocked_reasons:
        if {
            "vault_not_found",
            "alexandria_root_not_found",
            "managed_markdown_not_found",
            "source_snapshot_unreadable",
        } & set(blocked_reasons):
            return ["inspect_vault_configuration"]
        return ["resolve_recovery_blockers"]
    warning_set = set(warnings)
    if {"database_unreachable", "database_integrity_not_healthy"} & warning_set:
        return ["inspect_database"]
    if {
        "vault_not_found",
        "alexandria_root_not_found",
        "obsidian_stale_notes_present",
        "obsidian_error_notes_present",
    } & warning_set:
        return ["inspect_vault_configuration"]
    reconciliation_actions: list[str] = []
    if "memory_reconciliation_repository_unreachable" in warning_set:
        reconciliation_actions.append("inspect_memory_reconciliation_repository")
    if {
        "memory_reconciliation_partial_apply_present",
        "memory_reconciliation_failed_results_present",
    } & warning_set:
        reconciliation_actions.append("inspect_memory_reconciliation_failures")
    if "memory_reconciliation_hard_delete_detected" in warning_set:
        reconciliation_actions.append("audit_memory_reconciliation_integrity")
    if "memory_reconciliation_temporal_backfill_required" in warning_set:
        reconciliation_actions.append("preview_existing_memory_reconciliation")
    if {
        "memory_reconciliation_review_required",
        "memory_reconciliation_open_conflicts",
        "memory_reconciliation_reviews_in_progress",
    } & warning_set:
        reconciliation_actions.append("review_memory_reconciliation")
    if reconciliation_actions:
        return list(dict.fromkeys(reconciliation_actions))
    if status is OperationalReadinessStatus.RECOVERY_REQUIRED:
        return ["start_recovery_run"]
    return ["no_recovery_required"]


def _reconciliation_only_issue(warnings: list[str]) -> bool:
    """Return whether readiness contains only reconciliation-domain warnings."""
    return bool(warnings) and all(
        warning.startswith("memory_reconciliation_") for warning in warnings
    )
