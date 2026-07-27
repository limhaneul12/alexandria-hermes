"""Operational backup and isolated restore-drill behavior."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import anyio
import pytest
from app.operations.application.operational_backup_manifest import (
    OperationalBackupManifest,
)
from app.operations.application.operational_state_backup_service import (
    OperationalStateBackupService,
)
from app.operations.application.operational_state_restore_service import (
    OperationalStateRestoreService,
)
from app.shared.exceptions.common_exceptions import BoundaryValidationError


def _sqlite_with_state(path: Path, *, table: str, rows: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(path) as connection:
        connection.execute(f"CREATE TABLE {table} (id INTEGER PRIMARY KEY, value TEXT)")
        connection.executemany(
            f"INSERT INTO {table}(value) VALUES (?)",
            [(f"secret-state-{index}",) for index in range(rows)],
        )


def test_backup_and_restore_drill_verify_realistic_vault_and_sqlite_state(
    tmp_path: Path,
) -> None:
    """A 500-note snapshot must round-trip without touching live sources."""
    vault = tmp_path / "vault"
    root = vault / "Alexandria"
    for index in range(500):
        path = root / "Contexts" / f"note-{index:04d}.md"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            f"---\nid: note-{index}\nalexandria_type: context\n"
            "scope: GLOBAL\nstatus: active\n---\n\n"
            f"# Note {index}\n\nDurable content {index}\n",
            encoding="utf-8",
        )
    operational = tmp_path / "operational.sqlite"
    checkpoint = tmp_path / "checkpoint.sqlite"
    _sqlite_with_state(operational, table="provider_secrets", rows=8)
    _sqlite_with_state(checkpoint, table="checkpoints", rows=3)
    backup_root = tmp_path / "backups"

    async def scenario() -> tuple[OperationalBackupManifest, str, int, str]:
        backup = await OperationalStateBackupService(
            backup_root=str(backup_root),
            operational_database_path=str(operational),
            librarian_checkpoint_path=str(checkpoint),
        ).create(vault_path=str(vault), alexandria_root="Alexandria")
        manifest = OperationalBackupManifest.model_validate(
            json.loads(Path(backup.manifest_path).read_text(encoding="utf-8"))
        )
        drill = await OperationalStateRestoreService(
            backup_root=str(backup_root)
        ).drill(backup_id=backup.backup_id)
        return (
            manifest,
            drill.sqlite_integrity,
            drill.verified_artifacts,
            drill.restore_path,
        )

    manifest, sqlite_integrity, verified_artifacts, restore_path = anyio.run(scenario)

    assert len(manifest.artifacts) == 502
    assert {item.kind for item in manifest.artifacts} == {
        "canonical_vault",
        "operational_database",
        "librarian_checkpoint",
    }
    assert sqlite_integrity == "HEALTHY"
    assert verified_artifacts == 502
    assert Path(restore_path, "restore-drill-report.json").is_file()
    assert operational.is_file()
    assert checkpoint.is_file()
    assert len(list(root.rglob("*.md"))) == 500
    encrypted_note = next(
        item for item in manifest.artifacts if item.kind == "canonical_vault"
    )
    assert (
        b"Durable content"
        not in Path(
            backup_root / manifest.backup_id / encrypted_note.relative_path
        ).read_bytes()
    )


def test_backup_retention_prunes_only_old_published_backups(tmp_path: Path) -> None:
    """A verified publication prunes backups beyond the configured count."""
    vault = tmp_path / "vault"
    note = vault / "Alexandria" / "note.md"
    note.parent.mkdir(parents=True)
    note.write_text("# canonical", encoding="utf-8")
    operational = tmp_path / "operational.sqlite"
    _sqlite_with_state(operational, table="state", rows=1)
    backup_root = tmp_path / "backups"

    async def scenario() -> list[str]:
        service = OperationalStateBackupService(
            backup_root=str(backup_root),
            operational_database_path=str(operational),
            librarian_checkpoint_path=str(tmp_path / "missing.sqlite"),
            retention_count=2,
        )
        for _ in range(3):
            await service.create(vault_path=str(vault), alexandria_root="Alexandria")
        return sorted(
            path.name
            for path in backup_root.iterdir()
            if path.name.startswith("backup-")
        )

    retained = anyio.run(scenario)

    assert len(retained) == 2


def test_restore_drill_rejects_tampered_backup(tmp_path: Path) -> None:
    """Manifest hash mismatch must fail closed before restored state is trusted."""
    vault = tmp_path / "vault"
    note = vault / "Alexandria" / "note.md"
    note.parent.mkdir(parents=True)
    note.write_text("# canonical", encoding="utf-8")
    operational = tmp_path / "operational.sqlite"
    _sqlite_with_state(operational, table="state", rows=1)
    backup_root = tmp_path / "backups"

    async def scenario() -> None:
        backup = await OperationalStateBackupService(
            backup_root=str(backup_root),
            operational_database_path=str(operational),
            librarian_checkpoint_path=str(tmp_path / "missing-checkpoint.sqlite"),
        ).create(vault_path=str(vault), alexandria_root="Alexandria")
        manifest = OperationalBackupManifest.model_validate(
            json.loads(Path(backup.manifest_path).read_text(encoding="utf-8"))
        )
        vault_artifact = next(
            item for item in manifest.artifacts if item.kind == "canonical_vault"
        )
        Path(backup.backup_path, vault_artifact.relative_path).write_text(
            "tampered",
            encoding="utf-8",
        )
        with pytest.raises(
            BoundaryValidationError,
            match="artifact verification failed",
        ):
            await OperationalStateRestoreService(backup_root=str(backup_root)).drill(
                backup_id=backup.backup_id
            )

    anyio.run(scenario)
