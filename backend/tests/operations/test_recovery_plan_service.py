"""Operational recovery dry-run plan contracts."""

from __future__ import annotations

from pathlib import Path

import anyio
import pytest
import app.operations.application.recovery_plan_service as recovery_plan_module
from app.memory.domain.entities.context_read_models import RagDependencyHealth
from app.memory.domain.event_enum.context_enums import RagHealthState, RagStrategy
from app.obsidian.domain.entities.obsidian_note import ObsidianVaultStatus
from app.operations.application.recovery_plan_service import (
    RecoveryPlanRequest,
    RecoveryPlanService,
)
from app.operations.domain.event_enum.operational_readiness_enums import (
    OperationalReadinessStatus,
)
from app.shared.infrastructure.database import Database


class _FakeContextService:
    async def rag_health_with_index_status(self) -> RagDependencyHealth:
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


class _FakeObsidianService:
    def __init__(self, vault: Path, *, root_exists: bool = True) -> None:
        self._vault = vault
        self._root_exists = root_exists

    async def status(self) -> ObsidianVaultStatus:
        return ObsidianVaultStatus(
            vault_path=str(self._vault),
            alexandria_root="Alexandria",
            vault_exists=self._vault.exists(),
            alexandria_root_exists=self._root_exists
            and (self._vault / "Alexandria").exists(),
            indexed_notes=1,
            stale_notes=0,
            error_notes=0,
        )


def _write_vault_note(tmp_path: Path) -> tuple[Path, bytes]:
    note = tmp_path / "vault" / "Alexandria" / "Contexts" / "Projects" / "note.md"
    note.parent.mkdir(parents=True)
    body = b"---\nid: note\n---\n# Note\n"
    note.write_bytes(body)
    return note, body


def test_recovery_plan_for_sqlite_corruption_is_read_only_and_actionable(
    tmp_path: Path,
) -> None:
    """Dry-run should plan quarantine/rebuild without moving DB or editing vault files."""

    async def scenario() -> tuple[
        str, bool, list[str], list[str], list[str], bytes, bytes
    ]:
        database_path = tmp_path / "corrupt.db"
        corrupt_bytes = b"not a sqlite database"
        database_path.write_bytes(corrupt_bytes)
        wal_path = tmp_path / "corrupt.db-wal"
        shm_path = tmp_path / "corrupt.db-shm"
        wal_path.write_bytes(b"wal")
        shm_path.write_bytes(b"shm")
        note, note_before = _write_vault_note(tmp_path)
        database = Database(database_url=f"sqlite+aiosqlite:///{database_path}")
        service = RecoveryPlanService(
            database=database,
            context_service=_FakeContextService(),
            obsidian_service=_FakeObsidianService(tmp_path / "vault"),
        )

        plan = await service.plan(
            RecoveryPlanRequest(
                trigger="manual",
                actor="pytest",
                idempotency_key="plan-key-1",
            )
        )

        return (
            plan.status,
            plan.automatic_execution_allowed,
            [artifact.source_path for artifact in plan.quarantine_artifacts],
            [step.code for step in plan.steps],
            plan.blocked_reasons,
            database_path.read_bytes(),
            note.read_bytes(),
        )

    status, automatic, source_paths, steps, blocked, db_after, note_after = anyio.run(
        scenario
    )

    assert status == OperationalReadinessStatus.RECOVERY_REQUIRED
    assert automatic is True
    assert blocked == []
    assert source_paths == [
        str(tmp_path / "corrupt.db"),
        str(tmp_path / "corrupt.db-wal"),
        str(tmp_path / "corrupt.db-shm"),
    ]
    assert steps == [
        "snapshot_sources",
        "dispose_connections",
        "quarantine_sqlite_files",
        "rebuild_database_schema",
        "reindex_vault",
        "reindex_embeddings",
        "verify_readiness",
    ]
    assert db_after == b"not a sqlite database"
    assert note_after == b"---\nid: note\n---\n# Note\n"


def test_recovery_plan_blocks_without_readable_vault_source(tmp_path: Path) -> None:
    """Plan should not be executable when source Markdown preconditions fail."""

    async def scenario() -> tuple[str, bool, list[str], list[str]]:
        database_path = tmp_path / "corrupt.db"
        database_path.write_bytes(b"not a sqlite database")
        vault = tmp_path / "vault"
        vault.mkdir()
        database = Database(database_url=f"sqlite+aiosqlite:///{database_path}")
        service = RecoveryPlanService(
            database=database,
            context_service=_FakeContextService(),
            obsidian_service=_FakeObsidianService(vault, root_exists=False),
        )

        plan = await service.plan(RecoveryPlanRequest())
        return (
            plan.status,
            plan.automatic_execution_allowed,
            plan.blocked_reasons,
            plan.next_actions,
        )

    status, automatic, blocked, next_actions = anyio.run(scenario)

    assert status == OperationalReadinessStatus.BLOCKED
    assert automatic is False
    assert blocked == ["alexandria_root_not_found", "managed_markdown_not_found"]
    assert next_actions == ["inspect_vault_configuration"]


def test_recovery_plan_blocks_when_source_snapshot_access_fails(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Plan should fail closed without mutation when source snapshot cannot be read."""

    def fail_disk_usage(path: Path):  # type: ignore[no-untyped-def]
        raise OSError(f"cannot inspect source path: {path}")

    async def scenario() -> tuple[
        str,
        bool,
        list[str],
        list[str],
        str | None,
        bytes,
        bytes,
        bytes,
    ]:
        database_path = tmp_path / "corrupt.db"
        corrupt_bytes = b"not a sqlite database"
        database_path.write_bytes(corrupt_bytes)
        note, note_before = _write_vault_note(tmp_path)
        monkeypatch.setattr(recovery_plan_module, "disk_usage", fail_disk_usage)
        database = Database(database_url=f"sqlite+aiosqlite:///{database_path}")
        service = RecoveryPlanService(
            database=database,
            context_service=_FakeContextService(),
            obsidian_service=_FakeObsidianService(tmp_path / "vault"),
        )

        plan = await service.plan(
            RecoveryPlanRequest(
                trigger="manual",
                actor="pytest",
                idempotency_key="source-snapshot-access-failure",
            )
        )
        return (
            plan.status,
            plan.automatic_execution_allowed,
            plan.blocked_reasons,
            plan.next_actions,
            plan.source_snapshot.access_error,
            database_path.read_bytes(),
            note.read_bytes(),
            note_before,
        )

    (
        status,
        automatic,
        blocked,
        next_actions,
        access_error,
        db_after,
        note_after,
        note_before,
    ) = anyio.run(scenario)

    assert status == OperationalReadinessStatus.BLOCKED
    assert automatic is False
    assert blocked == ["source_snapshot_unreadable"]
    assert next_actions == ["inspect_vault_configuration"]
    assert access_error == "source_snapshot_unreadable"
    assert db_after == b"not a sqlite database"
    assert note_after == note_before


def test_recovery_plan_does_not_rebuild_for_non_corruption_database_error(
    tmp_path: Path,
) -> None:
    """Non-corruption SQLite errors should not trigger quarantine/rebuild execution."""

    async def scenario() -> tuple[str, bool, list[str], list[str]]:
        database_path = tmp_path / "runtime-as-directory.db"
        database_path.mkdir()
        _write_vault_note(tmp_path)
        database = Database(database_url=f"sqlite+aiosqlite:///{database_path}")
        service = RecoveryPlanService(
            database=database,
            context_service=_FakeContextService(),
            obsidian_service=_FakeObsidianService(tmp_path / "vault"),
        )

        plan = await service.plan(
            RecoveryPlanRequest(
                trigger="manual",
                actor="pytest",
                idempotency_key="non-corruption-db-error",
            )
        )
        return (
            plan.status,
            plan.automatic_execution_allowed,
            plan.diagnosis,
            plan.next_actions,
        )

    status, automatic, diagnosis, next_actions = anyio.run(scenario)

    assert status == OperationalReadinessStatus.BLOCKED
    assert automatic is False
    assert diagnosis == ["database_unreachable"]
    assert next_actions == ["inspect_database"]
