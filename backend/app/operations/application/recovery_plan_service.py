"""Read-only recovery dry-run planning service."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path
from shutil import disk_usage
from uuid import NAMESPACE_URL, uuid5

from app.operations.application.operational_readiness_service import (
    ContextReadinessService,
    ObsidianReadinessService,
    OperationalReadinessService,
)
from app.operations.domain.entities.recovery_plan import (
    RecoveryPlan,
    RecoveryPlanStep,
    RecoveryQuarantineArtifactPlan,
    RecoverySourceSnapshot,
)
from app.operations.domain.event_enum.operational_readiness_enums import (
    OperationalReadinessStatus,
)
from app.shared.infrastructure.database import Database


@dataclass(frozen=True, slots=True)
class RecoveryPlanRequest:
    """Request data for a recovery dry-run plan."""

    trigger: str = "manual"
    actor: str = "operator"
    idempotency_key: str | None = None
    parent_run_id: str | None = None


class RecoveryPlanService:
    """Build read-only recovery plans without moving or deleting files."""

    def __init__(
        self,
        *,
        database: Database,
        context_service: ContextReadinessService,
        obsidian_service: ObsidianReadinessService,
    ) -> None:
        """Create service.

        Args:
            database: Shared database coordinator.
            context_service: Context/RAG service.
            obsidian_service: Obsidian vault service.
        """
        self._database = database
        self._context_service = context_service
        self._obsidian_service = obsidian_service

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
            diagnosis=_diagnosis(readiness),
            blocked_reasons=blocked_reasons,
            source_snapshot=source_snapshot,
            quarantine_artifacts=quarantine_artifacts,
            steps=_steps(),
            estimated_reindex_scope={
                "vault_indexed_notes": readiness.vault.indexed_notes,
                "managed_markdown_count": source_snapshot.managed_markdown_count,
                "embedding_strategy": readiness.rag.effective_strategy.value,
            },
            service_impact=[
                "search_blocked_until_verify"
                if automatic_execution_allowed
                else "no_mutation_planned"
            ],
            next_actions=_next_actions(
                status,
                blocked_reasons,
                readiness.warnings,
            ),
            readiness=readiness,
            warnings=readiness.warnings,
        )


def _default_idempotency_key(
    *, database_path: str | None, trigger: str, actor: str
) -> str:
    seed = f"{database_path or 'non-sqlite'}:{trigger}:{actor}"
    return sha256(seed.encode("utf-8")).hexdigest()[:24]


def _source_snapshot(
    *, vault_path: str, alexandria_root: str
) -> RecoverySourceSnapshot:
    vault = Path(vault_path)
    root = Path(vault_path) / alexandria_root
    access_error: str | None = None
    try:
        markdown_files = sorted(root.rglob("*.md")) if root.exists() else []
    except OSError:
        markdown_files = []
        access_error = "source_snapshot_unreadable"
    representative = markdown_files[0] if markdown_files else None
    try:
        representative_hash = _file_sha256(representative) if representative else None
    except OSError:
        representative_hash = None
        access_error = "source_snapshot_unreadable"
    free_bytes = None
    if root.exists():
        try:
            free_bytes = disk_usage(root).free
        except OSError:
            access_error = "source_snapshot_unreadable"
    return RecoverySourceSnapshot(
        vault_path=vault_path,
        alexandria_root=alexandria_root,
        managed_markdown_count=len(markdown_files),
        representative_path=None if representative is None else str(representative),
        representative_sha256=representative_hash,
        disk_free_bytes=free_bytes,
        access_error=access_error,
        markdown_manifest=_markdown_manifest(vault, markdown_files),
    )


def _markdown_manifest(vault: Path, markdown_files: list[Path]) -> dict[str, str]:
    return {
        str(path.relative_to(vault)): file_hash
        for path in markdown_files
        if (file_hash := _file_sha256(path)) is not None
    }


def _quarantine_artifacts(
    *, database_path: str | None, run_id: str, created_at: datetime
) -> list[RecoveryQuarantineArtifactPlan]:
    if database_path is None:
        return []
    timestamp = created_at.strftime("%Y%m%dT%H%M%SZ")
    source_paths = [
        Path(database_path),
        Path(f"{database_path}-wal"),
        Path(f"{database_path}-shm"),
    ]
    quarantine_dir = Path(database_path).parent / ".alexandria-recovery" / run_id
    return [
        RecoveryQuarantineArtifactPlan(
            source_path=str(source_path),
            quarantine_path=str(
                quarantine_dir / f"{timestamp}-{source_path.name}-{run_id}"
            ),
            exists=source_path.exists(),
            size_bytes=source_path.stat().st_size if source_path.exists() else None,
            sha256=_file_sha256(source_path) if source_path.exists() else None,
        )
        for source_path in source_paths
    ]


def _file_sha256(path: Path | None) -> str | None:
    if path is None or not path.exists() or not path.is_file():
        return None
    digest = sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _blocked_reasons(
    readiness,
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


def _plan_status(readiness, blocked_reasons: list[str]) -> OperationalReadinessStatus:
    if blocked_reasons:
        return OperationalReadinessStatus.BLOCKED
    if readiness.status is OperationalReadinessStatus.RECOVERY_REQUIRED:
        return OperationalReadinessStatus.RECOVERY_REQUIRED
    return readiness.status


def _diagnosis(readiness) -> list[str]:
    if readiness.database.corruption_detected:
        return ["SQLITE_CORRUPTION_DETECTED"]
    return list(readiness.warnings)


def _steps() -> list[RecoveryPlanStep]:
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
    if status is OperationalReadinessStatus.RECOVERY_REQUIRED:
        return ["start_recovery_run"]
    return ["no_recovery_required"]
