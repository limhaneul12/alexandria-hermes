"""Non-destructive restore drills for operational backup artifacts."""

from __future__ import annotations

import json
import shutil
import sqlite3
import uuid
from dataclasses import dataclass
from pathlib import Path

from anyio import to_thread
from cryptography.fernet import InvalidToken

from app.operations.application.operational_backup_manifest import (
    OperationalBackupManifest,
)
from app.operations.application.operational_state_backup_service import (
    operational_backup_cipher,
    safe_backup_artifact_path,
    sha256_file,
)
from app.shared.exceptions.common_exceptions import BoundaryValidationError


@dataclass(frozen=True, slots=True)
class OperationalRestoreDrillResult:
    """Hash and SQLite evidence from an isolated restore drill."""

    backup_id: str
    drill_id: str
    restore_path: str
    verified_artifacts: int
    total_bytes: int
    sqlite_integrity: str


class OperationalStateRestoreService:
    """Restore only into an isolated drill directory, never over live state."""

    def __init__(self, *, backup_root: str) -> None:
        self._backup_root = Path(backup_root).expanduser().resolve()

    async def drill(self, *, backup_id: str) -> OperationalRestoreDrillResult:
        """Verify and copy one backup into a new isolated destination.

        Args:
            backup_id: Published operational backup identifier.

        Returns:
            Isolated restore and SQLite integrity evidence.
        """
        return await to_thread.run_sync(self._drill_sync, backup_id)

    def _drill_sync(self, backup_id: str) -> OperationalRestoreDrillResult:
        if not backup_id.startswith("backup-") or "/" in backup_id:
            raise BoundaryValidationError("operational backup id is invalid")
        backup_path = (self._backup_root / backup_id).resolve()
        if self._backup_root not in backup_path.parents or not backup_path.is_dir():
            raise BoundaryValidationError("operational backup does not exist")
        manifest_path = backup_path / "manifest.json"
        try:
            manifest = OperationalBackupManifest.model_validate(
                json.loads(manifest_path.read_text(encoding="utf-8"))
            )
        except (OSError, ValueError) as exc:
            raise BoundaryValidationError(
                "operational backup manifest is invalid"
            ) from exc
        if manifest.backup_id != backup_id:
            raise BoundaryValidationError("operational backup manifest id mismatch")
        cipher = operational_backup_cipher(self._backup_root)
        drill_id = f"drill-{uuid.uuid4().hex[:12]}"
        restore_path = self._backup_root / ".restore-drills" / backup_id / drill_id
        if restore_path.exists():
            raise BoundaryValidationError("restore drill destination exists")
        restore_path.mkdir(parents=True)
        try:
            for item in manifest.artifacts:
                source = safe_backup_artifact_path(
                    backup_path,
                    item.relative_path,
                )
                if (
                    not source.is_file()
                    or source.stat().st_size != item.size_bytes
                    or sha256_file(source) != item.sha256
                ):
                    raise BoundaryValidationError(
                        "operational backup artifact verification failed"
                    )
                destination = safe_backup_artifact_path(
                    restore_path,
                    item.relative_path,
                )
                destination.parent.mkdir(parents=True, exist_ok=True)
                try:
                    plaintext = cipher.decrypt(source.read_bytes())
                except InvalidToken as exc:
                    raise BoundaryValidationError(
                        "operational backup decryption failed"
                    ) from exc
                destination.write_bytes(plaintext)
                if sha256_file(destination) != item.plaintext_sha256:
                    raise BoundaryValidationError(
                        "restored operational artifact hash mismatch"
                    )
            sqlite_results = [
                _sqlite_integrity(
                    safe_backup_artifact_path(
                        restore_path,
                        item.relative_path,
                    )
                )
                for item in manifest.artifacts
                if item.kind in {"operational_database", "librarian_checkpoint"}
            ]
            sqlite_integrity = (
                "HEALTHY"
                if sqlite_results and all(result == "ok" for result in sqlite_results)
                else "NOT_APPLICABLE"
            )
            report_path = restore_path / "restore-drill-report.json"
            report_path.write_text(
                json.dumps(
                    {
                        "backup_id": backup_id,
                        "drill_id": drill_id,
                        "verified_artifacts": len(manifest.artifacts),
                        "total_bytes": manifest.total_bytes,
                        "sqlite_integrity": sqlite_integrity,
                    },
                    ensure_ascii=False,
                    indent=2,
                    sort_keys=True,
                ),
                encoding="utf-8",
            )
            return OperationalRestoreDrillResult(
                backup_id=backup_id,
                drill_id=drill_id,
                restore_path=str(restore_path),
                verified_artifacts=len(manifest.artifacts),
                total_bytes=manifest.total_bytes,
                sqlite_integrity=sqlite_integrity,
            )
        except BaseException:
            shutil.rmtree(restore_path, ignore_errors=True)
            raise


def _sqlite_integrity(path: Path) -> str:
    uri = f"{path.as_uri()}?mode=ro"
    with sqlite3.connect(uri, uri=True) as connection:
        row = connection.execute("PRAGMA integrity_check").fetchone()
    return str(row[0]) if row else "missing"
