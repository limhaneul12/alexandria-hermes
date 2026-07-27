"""Read-only recovery dry-run planning service."""

from __future__ import annotations

from datetime import UTC, datetime
from shutil import disk_usage
from uuid import NAMESPACE_URL, uuid5

from app.operations.application.operational_readiness_contracts import (
    ContextReadinessService,
    ObsidianReadinessService,
    ReconciliationReadinessService,
)
from app.operations.application.operational_readiness_service import (
    OperationalReadinessService,
)
from app.operations.application.recovery_plan_contracts import RecoveryPlanRequest
from app.operations.application.recovery_plan_policy import (
    _blocked_reasons,
    _default_idempotency_key,
    _diagnosis,
    _next_actions,
    _plan_status,
    _steps,
)
from app.operations.application.recovery_plan_source_policy import (
    _quarantine_artifacts,
    _source_snapshot,
)
from app.operations.domain.entities.recovery_plan import RecoveryPlan
from app.operations.domain.event_enum.operational_readiness_enums import (
    OperationalReadinessStatus,
)
from app.shared.infrastructure.database import Database

__all__ = (
    "RecoveryPlanRequest",
    "RecoveryPlanService",
)


class RecoveryPlanService:
    """Build read-only recovery plans without moving or deleting files."""

    def __init__(
        self,
        *,
        database: Database,
        context_service: ContextReadinessService,
        obsidian_service: ObsidianReadinessService,
        reconciliation_service: ReconciliationReadinessService | None = None,
    ) -> None:
        """Create service.

        Args:
            database: Shared database coordinator.
            context_service: Context/RAG service.
            obsidian_service: Obsidian vault service.
            reconciliation_service: Optional memory reconciliation diagnostics.
        """
        self._database = database
        self._context_service = context_service
        self._obsidian_service = obsidian_service
        self._reconciliation_service = reconciliation_service

    async def plan(self, request: RecoveryPlanRequest) -> RecoveryPlan:
        """Return a read-only recovery dry-run plan.

        Args:
            request: Recovery plan input contract.

        Returns:
            Recovery dry-run plan.
        """
        readiness_service = OperationalReadinessService(
            database=self._database,
            context_service=self._context_service,
            obsidian_service=self._obsidian_service,
            reconciliation_service=self._reconciliation_service,
        )
        readiness = await readiness_service.snapshot()
        created_at = datetime.now(UTC)
        database_path = self._database.sqlite_path
        idempotency_key = request.idempotency_key or _default_idempotency_key(
            database_path=database_path,
            trigger=request.trigger,
            actor=request.actor,
        )
        run_id = str(
            uuid5(
                NAMESPACE_URL,
                f"alexandria-hermes:recovery:{database_path}:{idempotency_key}",
            )
        )
        source_snapshot = _source_snapshot(
            vault_path=readiness.vault.vault_path,
            alexandria_root=readiness.vault.alexandria_root,
            disk_usage_provider=disk_usage,
        )
        quarantine_artifacts = _quarantine_artifacts(
            database_path=database_path,
            run_id=run_id,
            created_at=created_at,
        )
        blocked_reasons = _blocked_reasons(readiness, source_snapshot, database_path)
        status = _plan_status(readiness, blocked_reasons)
        automatic_execution_allowed = (
            status is OperationalReadinessStatus.RECOVERY_REQUIRED
            and not blocked_reasons
            and database_path is not None
        )
        return RecoveryPlan(
            id=run_id,
            parent_run_id=request.parent_run_id,
            idempotency_key=idempotency_key,
            trigger=request.trigger,
            actor=request.actor,
            status=status,
            created_at=created_at,
            target_database_path=database_path,
            dry_run=True,
            deletion_performed=False,
            automatic_execution_allowed=automatic_execution_allowed,
            diagnosis=tuple(_diagnosis(readiness)),
            blocked_reasons=tuple(blocked_reasons),
            source_snapshot=source_snapshot,
            quarantine_artifacts=tuple(quarantine_artifacts),
            steps=tuple(_steps(readiness)),
            estimated_reindex_scope={
                "vault_indexed_notes": readiness.vault.indexed_notes,
                "managed_markdown_count": source_snapshot.managed_markdown_count,
                "embedding_strategy": readiness.rag.effective_strategy.value,
            },
            service_impact=(
                (
                    "search_blocked_until_verify"
                    if automatic_execution_allowed
                    else "no_mutation_planned"
                ),
            ),
            next_actions=tuple(
                _next_actions(
                    status,
                    blocked_reasons,
                    list(readiness.warnings),
                )
            ),
            readiness=readiness,
            warnings=tuple(readiness.warnings),
        )
