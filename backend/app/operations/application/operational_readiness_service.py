"""Read-only operational readiness snapshot service."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Protocol, cast

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.memory.domain.entities.context_read_models import RagDependencyHealth
from app.memory.domain.event_enum.context_enums import RagHealthState, RagStrategy
from app.obsidian.domain.entities.obsidian_note import ObsidianVaultStatus
from app.operations.domain.entities.operational_readiness import (
    OperationalDatabaseSnapshot,
    OperationalRagSnapshot,
    OperationalReadinessSnapshot,
    OperationalVaultSnapshot,
)
from app.operations.domain.event_enum.operational_readiness_enums import (
    OperationalReadinessStatus,
)
from app.operations.domain.recovery_state_constants import (
    UNREADABLE_ACTIVE_RECOVERY_RUN_ID,
)
from app.shared.infrastructure.database import Database, is_sqlite_corruption_error
from app.shared.serialization.orjson_codec import loads_json


class ContextReadinessService(Protocol):
    """Subset of ContextService needed for readiness."""

    async def rag_health_with_index_status(self) -> RagDependencyHealth:
        """Return RAG health including persisted index status.

        Returns:
            RAG dependency health snapshot.
        """


class ObsidianReadinessService(Protocol):
    """Subset of ObsidianService needed for readiness."""

    async def status(self) -> ObsidianVaultStatus:
        """Return vault/index status.

        Returns:
            Obsidian vault/index status snapshot.
        """


class OperationalReadinessService:
    """Build operational readiness snapshots without mutating recovery state."""

    def __init__(
        self,
        *,
        database: Database,
        context_service: ContextReadinessService,
        obsidian_service: ObsidianReadinessService,
        ignore_active_recovery_run_id: str | None = None,
    ) -> None:
        """Create service.

        Args:
            database: Shared database coordinator.
            context_service: Context/RAG service.
            obsidian_service: Obsidian vault service.
            ignore_active_recovery_run_id: Active run id to ignore for internal
                verification.
        """
        self._database = database
        self._context_service = context_service
        self._obsidian_service = obsidian_service
        self._ignore_active_recovery_run_id = ignore_active_recovery_run_id

    async def snapshot(self) -> OperationalReadinessSnapshot:
        """Return current read-only operational readiness.

        Returns:
            Snapshot composed from database, vault, and RAG diagnostics.
        """
        started = datetime.now(UTC)
        database = await self._database_snapshot()
        vault_status = await self._obsidian_service.status()
        rag_health = await self._context_service.rag_health_with_index_status()
        vault = _vault_snapshot(vault_status)
        rag = _rag_snapshot(rag_health)
        active_recovery_run_id = _active_recovery_run_id(self._database.sqlite_path)
        if active_recovery_run_id == self._ignore_active_recovery_run_id:
            active_recovery_run_id = None
        last_successful_recovery_run_id = _last_successful_recovery_run_id(
            self._database.sqlite_path
        )
        warnings = _warnings(database=database, vault=vault, rag=rag)
        if active_recovery_run_id is not None:
            warnings.append("recovery_in_progress")
        blockers = _blockers(warnings)
        status = _status(
            database=database,
            vault=vault,
            rag=rag,
            warnings=warnings,
            active_recovery_run_id=active_recovery_run_id,
        )
        finished = datetime.now(UTC)
        return OperationalReadinessSnapshot(
            status=status,
            ready=status is OperationalReadinessStatus.READY,
            checked_at=finished,
            duration_ms=max(int((finished - started).total_seconds() * 1000), 0),
            vault=vault,
            database=database,
            rag=rag,
            active_recovery_run_id=active_recovery_run_id,
            last_successful_recovery_run_id=last_successful_recovery_run_id,
            warnings=warnings,
            blockers=blockers,
            next_actions=_next_actions(warnings),
        )

    async def _database_snapshot(self) -> OperationalDatabaseSnapshot:
        try:
            async with self._database.session_factory()() as session:
                quick_check = await session.scalar(text("PRAGMA quick_check"))
                schema_version = await _schema_version(session)
        except SQLAlchemyError as exc:
            corruption = is_sqlite_corruption_error(exc)
            return OperationalDatabaseSnapshot(
                reachable=False,
                integrity="CORRUPTION_DETECTED" if corruption else "UNAVAILABLE",
                schema_version=None,
                corruption_detected=corruption,
            )
        integrity = "HEALTHY" if quick_check == "ok" else "FAILED"
        return OperationalDatabaseSnapshot(
            reachable=True,
            integrity=integrity,
            schema_version=schema_version,
            corruption_detected=False,
        )


async def _schema_version(session) -> str | None:
    table_exists = await session.scalar(
        text(
            "SELECT name FROM sqlite_master "
            "WHERE type = 'table' AND name = 'alembic_version'"
        )
    )
    if table_exists is None:
        return "unknown"
    version = await session.scalar(text("SELECT version_num FROM alembic_version"))
    return None if version is None else str(version)


def _vault_snapshot(status: ObsidianVaultStatus) -> OperationalVaultSnapshot:
    return OperationalVaultSnapshot(
        exists=status.vault_exists,
        readable=status.vault_exists and status.alexandria_root_exists,
        vault_path=status.vault_path,
        alexandria_root=status.alexandria_root,
        alexandria_root_exists=status.alexandria_root_exists,
        indexed_notes=status.indexed_notes,
        stale_notes=status.stale_notes,
        error_notes=status.error_notes,
    )


def _rag_snapshot(health: RagDependencyHealth) -> OperationalRagSnapshot:
    return OperationalRagSnapshot(
        fts=health.fts,
        vector=health.vector,
        embedding=health.embedding,
        effective_strategy=health.default_strategy,
        model_name=health.model_name,
        dimensions=health.dimensions,
        fingerprint=health.fingerprint,
        source_statuses=health.source_statuses,
        warnings=health.warnings,
    )


def _warnings(
    *,
    database: OperationalDatabaseSnapshot,
    vault: OperationalVaultSnapshot,
    rag: OperationalRagSnapshot,
) -> list[str]:
    warnings: list[str] = []
    if database.corruption_detected:
        warnings.append("sqlite_corruption_detected")
    elif not database.reachable:
        warnings.append("database_unreachable")
    elif database.integrity != "HEALTHY":
        warnings.append("database_integrity_not_healthy")
    if not vault.exists:
        warnings.append("vault_not_found")
    if not vault.alexandria_root_exists:
        warnings.append("alexandria_root_not_found")
    if vault.stale_notes > 0:
        warnings.append("obsidian_stale_notes_present")
    if vault.error_notes > 0:
        warnings.append("obsidian_error_notes_present")
    if rag.fts is not RagHealthState.HEALTHY:
        warnings.append("rag_fts_not_healthy")
    if rag.vector is not RagHealthState.HEALTHY:
        warnings.append("rag_vector_not_healthy")
    if rag.embedding is RagHealthState.REINDEX_REQUIRED:
        warnings.append("rag_embedding_reindex_required")
    elif rag.embedding is not RagHealthState.HEALTHY:
        warnings.append("rag_embedding_not_healthy")
    if (
        rag.fts is RagHealthState.HEALTHY
        and rag.vector is RagHealthState.HEALTHY
        and rag.embedding is RagHealthState.HEALTHY
        and rag.effective_strategy is not RagStrategy.HYBRID
    ):
        warnings.append("rag_default_strategy_not_hybrid")
    if (
        rag.fts is RagHealthState.HEALTHY
        and rag.vector is RagHealthState.HEALTHY
        and rag.embedding is RagHealthState.HEALTHY
        and rag.warnings
    ):
        warnings.append("rag_status_warnings_present")
    return warnings


def _blockers(warnings: list[str]) -> list[str]:
    blocking_codes = {
        "database_unreachable",
        "database_integrity_not_healthy",
        "sqlite_corruption_detected",
        "vault_not_found",
        "alexandria_root_not_found",
        "obsidian_stale_notes_present",
        "obsidian_error_notes_present",
        "rag_fts_not_healthy",
        "rag_default_strategy_not_hybrid",
        "rag_status_warnings_present",
        "recovery_in_progress",
    }
    return [warning for warning in warnings if warning in blocking_codes]


def _status(
    *,
    database: OperationalDatabaseSnapshot,
    vault: OperationalVaultSnapshot,
    rag: OperationalRagSnapshot,
    warnings: list[str],
    active_recovery_run_id: str | None,
) -> OperationalReadinessStatus:
    if active_recovery_run_id is not None:
        return OperationalReadinessStatus.RECOVERING
    if database.corruption_detected:
        return OperationalReadinessStatus.RECOVERY_REQUIRED
    blockers = _blockers(warnings)
    if blockers:
        return OperationalReadinessStatus.BLOCKED
    if (
        rag.fts is RagHealthState.HEALTHY
        and rag.effective_strategy is RagStrategy.FTS_ONLY
        and (
            rag.vector is not RagHealthState.HEALTHY
            or rag.embedding is not RagHealthState.HEALTHY
        )
    ):
        return OperationalReadinessStatus.DEGRADED_FTS_ONLY
    if warnings:
        return OperationalReadinessStatus.UNKNOWN
    return OperationalReadinessStatus.READY


def _next_actions(warnings: list[str]) -> list[str]:
    actions: list[str] = []
    warning_set = set(warnings)
    if "sqlite_corruption_detected" in warning_set:
        actions.append("plan_recovery")
    if {
        "vault_not_found",
        "alexandria_root_not_found",
        "obsidian_stale_notes_present",
        "obsidian_error_notes_present",
    } & warning_set:
        actions.append("reindex_vault")
    if {
        "rag_vector_not_healthy",
        "rag_embedding_reindex_required",
        "rag_embedding_not_healthy",
        "rag_default_strategy_not_hybrid",
        "rag_status_warnings_present",
    } & warning_set:
        actions.append("reindex_embeddings")
    if "database_unreachable" in warning_set:
        actions.append("inspect_database")
    if "recovery_in_progress" in warning_set:
        actions.append("inspect_recovery_run")
    return actions


def _active_recovery_run_id(database_path: str | None) -> str | None:
    path = _recovery_dir(database_path) / "active-run.json"
    if not path.exists():
        return None
    payload = _load_recovery_json(path)
    if payload is None:
        return UNREADABLE_ACTIVE_RECOVERY_RUN_ID
    run_id = payload.get("run_id")
    return UNREADABLE_ACTIVE_RECOVERY_RUN_ID if run_id is None else str(run_id)


def _last_successful_recovery_run_id(database_path: str | None) -> str | None:
    recovery_dir = _recovery_dir(database_path)
    if not recovery_dir.exists():
        return None
    completed: list[tuple[str, str]] = []
    for manifest_path in recovery_dir.glob("*/recovery-run.json"):
        payload = _load_recovery_json(manifest_path)
        if payload is None or payload.get("status") != "COMPLETED":
            continue
        run_id = payload.get("id")
        if run_id is None:
            continue
        finished_at = (
            payload.get("finished_at")
            or payload.get("updated_at")
            or payload.get("started_at")
            or ""
        )
        completed.append((str(finished_at), str(run_id)))
    if not completed:
        return None
    return max(completed)[1]


def _recovery_dir(database_path: str | None) -> Path:
    if database_path is None:
        return Path.cwd() / ".alexandria-recovery"
    return Path(database_path).parent / ".alexandria-recovery"


def _load_recovery_json(path: Path) -> dict[str, Any] | None:
    try:
        payload = loads_json(path.read_bytes())
    except (OSError, ValueError):
        return None
    if not isinstance(payload, dict):
        return None
    return cast(dict[str, Any], payload)
