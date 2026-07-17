"""Operational readiness snapshot contracts."""

from __future__ import annotations

from pathlib import Path

import anyio
from app.memory.domain.entities.context_read_models import RagDependencyHealth
from app.memory.domain.event_enum.context_enums import RagHealthState, RagStrategy
from app.obsidian.domain.entities.obsidian_note import ObsidianVaultStatus
from app.operations.application.operational_readiness_service import (
    OperationalReadinessService,
)
from app.operations.domain.event_enum.operational_readiness_enums import (
    OperationalReadinessStatus,
)
from app.shared.infrastructure.database import Database


class _FakeContextService:
    def __init__(self, health: RagDependencyHealth) -> None:
        self._health = health

    async def rag_health_with_index_status(self) -> RagDependencyHealth:
        return self._health


class _FakeObsidianService:
    def __init__(self, status: ObsidianVaultStatus) -> None:
        self._status = status

    async def status(self) -> ObsidianVaultStatus:
        return self._status


def _healthy_rag() -> RagDependencyHealth:
    return RagDependencyHealth(
        fts=RagHealthState.HEALTHY,
        vector=RagHealthState.HEALTHY,
        embedding=RagHealthState.HEALTHY,
        default_strategy=RagStrategy.HYBRID,
        model_name="test-model",
        dimensions=3,
        fingerprint={"provider": "test"},
        warnings=[],
    )


def _degraded_embedding_rag() -> RagDependencyHealth:
    return RagDependencyHealth(
        fts=RagHealthState.HEALTHY,
        vector=RagHealthState.HEALTHY,
        embedding=RagHealthState.REINDEX_REQUIRED,
        default_strategy=RagStrategy.FTS_ONLY,
        model_name="test-model",
        dimensions=3,
        fingerprint={"provider": "test"},
        warnings=["embedding fingerprint mismatch"],
    )


def _healthy_components_fts_only_rag() -> RagDependencyHealth:
    return RagDependencyHealth(
        fts=RagHealthState.HEALTHY,
        vector=RagHealthState.HEALTHY,
        embedding=RagHealthState.HEALTHY,
        default_strategy=RagStrategy.FTS_ONLY,
        model_name="test-model",
        dimensions=3,
        fingerprint={"provider": "test"},
        warnings=[],
    )


def _healthy_components_warning_rag() -> RagDependencyHealth:
    return RagDependencyHealth(
        fts=RagHealthState.HEALTHY,
        vector=RagHealthState.HEALTHY,
        embedding=RagHealthState.HEALTHY,
        default_strategy=RagStrategy.HYBRID,
        model_name="test-model",
        dimensions=3,
        fingerprint={"provider": "test"},
        warnings=["vector index is stale"],
    )


def _obsidian_status(
    tmp_path: Path, *, stale: int = 0, errors: int = 0
) -> ObsidianVaultStatus:
    vault = tmp_path / "vault"
    root = vault / "Alexandria"
    root.mkdir(parents=True)
    return ObsidianVaultStatus(
        vault_path=str(vault),
        alexandria_root="Alexandria",
        vault_exists=True,
        alexandria_root_exists=True,
        indexed_notes=3,
        stale_notes=stale,
        error_notes=errors,
    )


def test_operational_readiness_reports_ready_when_all_dependencies_are_healthy(
    tmp_path: Path,
) -> None:
    """Healthy database, vault, and RAG should produce READY/HYBRID."""

    async def scenario() -> tuple[str, bool, str, list[str]]:
        database = Database(
            database_url=f"sqlite+aiosqlite:///{tmp_path / 'ready.db'}",
            create_schema=True,
        )
        await database.initialize()
        try:
            service = OperationalReadinessService(
                database=database,
                context_service=_FakeContextService(_healthy_rag()),
                obsidian_service=_FakeObsidianService(_obsidian_status(tmp_path)),
            )

            snapshot = await service.snapshot()
            return (
                snapshot.status,
                snapshot.ready,
                snapshot.rag.effective_strategy,
                snapshot.warnings,
            )
        finally:
            await database.shutdown()

    status, ready, strategy, warnings = anyio.run(scenario)

    assert status == OperationalReadinessStatus.READY
    assert ready is True
    assert strategy == RagStrategy.HYBRID
    assert warnings == []


def test_operational_readiness_blocks_when_rag_strategy_is_not_hybrid(
    tmp_path: Path,
) -> None:
    """All RAG components healthy still requires HYBRID default strategy."""

    async def scenario() -> tuple[str, bool, str, list[str], list[str]]:
        database = Database(
            database_url=f"sqlite+aiosqlite:///{tmp_path / 'fts-only.db'}",
            create_schema=True,
        )
        await database.initialize()
        try:
            service = OperationalReadinessService(
                database=database,
                context_service=_FakeContextService(_healthy_components_fts_only_rag()),
                obsidian_service=_FakeObsidianService(_obsidian_status(tmp_path)),
            )

            snapshot = await service.snapshot()
            return (
                snapshot.status,
                snapshot.ready,
                snapshot.rag.effective_strategy,
                snapshot.warnings,
                snapshot.blockers,
            )
        finally:
            await database.shutdown()

    status, ready, strategy, warnings, blockers = anyio.run(scenario)

    assert status == OperationalReadinessStatus.BLOCKED
    assert ready is False
    assert strategy == RagStrategy.FTS_ONLY
    assert warnings == ["rag_default_strategy_not_hybrid"]
    assert blockers == ["rag_default_strategy_not_hybrid"]


def test_operational_readiness_blocks_when_rag_health_reports_warnings(
    tmp_path: Path,
) -> None:
    """RAG health warnings should prevent operational READY."""

    async def scenario() -> tuple[str, bool, list[str], list[str]]:
        database = Database(
            database_url=f"sqlite+aiosqlite:///{tmp_path / 'rag-warning.db'}",
            create_schema=True,
        )
        await database.initialize()
        try:
            service = OperationalReadinessService(
                database=database,
                context_service=_FakeContextService(_healthy_components_warning_rag()),
                obsidian_service=_FakeObsidianService(_obsidian_status(tmp_path)),
            )

            snapshot = await service.snapshot()
            return snapshot.status, snapshot.ready, snapshot.warnings, snapshot.blockers
        finally:
            await database.shutdown()

    status, ready, warnings, blockers = anyio.run(scenario)

    assert status == OperationalReadinessStatus.BLOCKED
    assert ready is False
    assert warnings == ["rag_status_warnings_present"]
    assert blockers == ["rag_status_warnings_present"]


def test_operational_readiness_degrades_to_fts_only_when_embedding_reindex_required(
    tmp_path: Path,
) -> None:
    """Embedding mismatch should be visible as DEGRADED_FTS_ONLY, not READY."""

    async def scenario() -> tuple[str, bool, str, list[str], list[str]]:
        database = Database(
            database_url=f"sqlite+aiosqlite:///{tmp_path / 'degraded.db'}",
            create_schema=True,
        )
        await database.initialize()
        try:
            service = OperationalReadinessService(
                database=database,
                context_service=_FakeContextService(_degraded_embedding_rag()),
                obsidian_service=_FakeObsidianService(_obsidian_status(tmp_path)),
            )

            snapshot = await service.snapshot()
            return (
                snapshot.status,
                snapshot.ready,
                snapshot.rag.effective_strategy,
                snapshot.warnings,
                snapshot.next_actions,
            )
        finally:
            await database.shutdown()

    status, ready, strategy, warnings, next_actions = anyio.run(scenario)

    assert status == OperationalReadinessStatus.DEGRADED_FTS_ONLY
    assert ready is False
    assert strategy == RagStrategy.FTS_ONLY
    assert "rag_embedding_reindex_required" in warnings
    assert "reindex_embeddings" in next_actions


def test_operational_readiness_blocks_when_vault_has_index_errors(
    tmp_path: Path,
) -> None:
    """Vault stale/error notes should prevent READY until reindex repair succeeds."""

    async def scenario() -> tuple[str, bool, list[str], list[str]]:
        database = Database(
            database_url=f"sqlite+aiosqlite:///{tmp_path / 'blocked.db'}",
            create_schema=True,
        )
        await database.initialize()
        try:
            service = OperationalReadinessService(
                database=database,
                context_service=_FakeContextService(_healthy_rag()),
                obsidian_service=_FakeObsidianService(
                    _obsidian_status(tmp_path, stale=1, errors=1)
                ),
            )

            snapshot = await service.snapshot()
            return (
                snapshot.status,
                snapshot.ready,
                snapshot.warnings,
                snapshot.next_actions,
            )
        finally:
            await database.shutdown()

    status, ready, warnings, next_actions = anyio.run(scenario)

    assert status == OperationalReadinessStatus.BLOCKED
    assert ready is False
    assert warnings == ["obsidian_stale_notes_present", "obsidian_error_notes_present"]
    assert "reindex_vault" in next_actions


def test_operational_readiness_marks_sqlite_corruption_as_recovery_required(
    tmp_path: Path,
) -> None:
    """Non-database SQLite bytes should become RECOVERY_REQUIRED diagnostics."""

    async def scenario() -> tuple[str, bool, str, list[str]]:
        database_path = tmp_path / "corrupt.db"
        database_path.write_bytes(b"not a sqlite database")
        database = Database(database_url=f"sqlite+aiosqlite:///{database_path}")
        service = OperationalReadinessService(
            database=database,
            context_service=_FakeContextService(_healthy_rag()),
            obsidian_service=_FakeObsidianService(_obsidian_status(tmp_path)),
        )

        snapshot = await service.snapshot()
        return (
            snapshot.status,
            snapshot.ready,
            snapshot.database.integrity,
            snapshot.warnings,
        )

    status, ready, integrity, warnings = anyio.run(scenario)

    assert status == OperationalReadinessStatus.RECOVERY_REQUIRED
    assert ready is False
    assert integrity == "CORRUPTION_DETECTED"
    assert warnings == ["sqlite_corruption_detected"]


def test_operational_readiness_reports_active_recovery_lock(tmp_path: Path) -> None:
    """Active recovery lock should fail closed as RECOVERING."""

    async def scenario() -> tuple[str, bool, str | None, list[str], list[str]]:
        database = Database(
            database_url=f"sqlite+aiosqlite:///{tmp_path / 'active.db'}",
            create_schema=True,
        )
        await database.initialize()
        recovery_dir = tmp_path / ".alexandria-recovery"
        recovery_dir.mkdir()
        (recovery_dir / "active-run.json").write_text(
            '{"run_id":"active-run","idempotency_key":"active-key"}',
            encoding="utf-8",
        )
        try:
            service = OperationalReadinessService(
                database=database,
                context_service=_FakeContextService(_healthy_rag()),
                obsidian_service=_FakeObsidianService(_obsidian_status(tmp_path)),
            )

            snapshot = await service.snapshot()
            return (
                snapshot.status,
                snapshot.ready,
                snapshot.active_recovery_run_id,
                snapshot.blockers,
                snapshot.next_actions,
            )
        finally:
            await database.shutdown()

    status, ready, active_run_id, blockers, next_actions = anyio.run(scenario)

    assert status == OperationalReadinessStatus.RECOVERING
    assert ready is False
    assert active_run_id == "active-run"
    assert "recovery_in_progress" in blockers
    assert "inspect_recovery_run" in next_actions


def test_operational_readiness_reports_unreadable_active_recovery_lock(
    tmp_path: Path,
) -> None:
    """Corrupt restart state should still fail closed as recovery in progress."""

    async def scenario() -> tuple[str, bool, str | None, list[str], list[str]]:
        database = Database(
            database_url=f"sqlite+aiosqlite:///{tmp_path / 'corrupt-lock.db'}",
            create_schema=True,
        )
        await database.initialize()
        recovery_dir = tmp_path / ".alexandria-recovery"
        recovery_dir.mkdir()
        (recovery_dir / "active-run.json").write_text("{not-json", encoding="utf-8")
        try:
            service = OperationalReadinessService(
                database=database,
                context_service=_FakeContextService(_healthy_rag()),
                obsidian_service=_FakeObsidianService(_obsidian_status(tmp_path)),
            )

            snapshot = await service.snapshot()
            return (
                snapshot.status,
                snapshot.ready,
                snapshot.active_recovery_run_id,
                snapshot.blockers,
                snapshot.next_actions,
            )
        finally:
            await database.shutdown()

    status, ready, active_run_id, blockers, next_actions = anyio.run(scenario)

    assert status == OperationalReadinessStatus.RECOVERING
    assert ready is False
    assert active_run_id == "unreadable-active-recovery-lock"
    assert "recovery_in_progress" in blockers
    assert "inspect_recovery_run" in next_actions


def test_operational_readiness_reports_last_successful_recovery_run(
    tmp_path: Path,
) -> None:
    """Readiness should expose the most recent completed recovery run id."""

    async def scenario() -> tuple[str, str | None]:
        database = Database(
            database_url=f"sqlite+aiosqlite:///{tmp_path / 'last.db'}",
            create_schema=True,
        )
        await database.initialize()
        recovery_dir = tmp_path / ".alexandria-recovery"
        (recovery_dir / "failed-run").mkdir(parents=True)
        (recovery_dir / "failed-run" / "recovery-run.json").write_text(
            '{"id":"failed-run","status":"FAILED","finished_at":"2026-07-16T00:00:00+00:00"}',
            encoding="utf-8",
        )
        (recovery_dir / "completed-run").mkdir(parents=True)
        (recovery_dir / "completed-run" / "recovery-run.json").write_text(
            '{"id":"completed-run","status":"COMPLETED",'
            '"finished_at":"2026-07-16T01:00:00+00:00"}',
            encoding="utf-8",
        )
        try:
            service = OperationalReadinessService(
                database=database,
                context_service=_FakeContextService(_healthy_rag()),
                obsidian_service=_FakeObsidianService(_obsidian_status(tmp_path)),
            )

            snapshot = await service.snapshot()
            return snapshot.status, snapshot.last_successful_recovery_run_id
        finally:
            await database.shutdown()

    status, last_successful_recovery_run_id = anyio.run(scenario)

    assert status == OperationalReadinessStatus.READY
    assert last_successful_recovery_run_id == "completed-run"
