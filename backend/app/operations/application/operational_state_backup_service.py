"""Consistent local backups for canonical notes and non-rebuildable state."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import sqlite3
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal

from anyio import to_thread
from cryptography.fernet import Fernet

from app.operations.application.operational_backup_manifest import (
    OperationalBackupArtifact,
    OperationalBackupManifest,
)
from app.shared.exceptions.common_exceptions import BoundaryValidationError
from app.shared.types.extra_types import JSONObject

_MANIFEST_NAME = "manifest.json"
_SYSTEM_VAULT_FOLDER = ".alexandria-hermes"
_KEY_FILE_NAME = ".operational-backup.key"


@dataclass(frozen=True, slots=True)
class OperationalBackupResult:
    """Evidence returned after an atomic backup directory is published."""

    backup_id: str
    backup_path: str
    manifest_path: str
    artifact_count: int
    total_bytes: int


class OperationalStateBackupService:
    """Snapshot canonical Vault files and SQLite state without exposing secrets."""

    def __init__(
        self,
        *,
        backup_root: str,
        operational_database_path: str,
        librarian_checkpoint_path: str,
        retention_count: int = 10,
    ) -> None:
        self._backup_root = Path(backup_root).expanduser().resolve()
        self._operational_database_path = (
            Path(operational_database_path).expanduser().resolve()
        )
        self._librarian_checkpoint_path = (
            Path(librarian_checkpoint_path).expanduser().resolve()
        )
        if retention_count < 1:
            raise BoundaryValidationError("backup retention count must be positive")
        self._retention_count = retention_count

    async def create(
        self,
        *,
        vault_path: str,
        alexandria_root: str,
    ) -> OperationalBackupResult:
        """Create and verify an atomic backup in a worker thread.

        Args:
            vault_path: Absolute or expanded Obsidian vault path.
            alexandria_root: Canonical managed root relative to the vault.

        Returns:
            Published backup evidence.
        """
        return await to_thread.run_sync(
            self._create_sync,
            Path(vault_path).expanduser().resolve(),
            alexandria_root,
        )

    def _create_sync(
        self,
        vault_path: Path,
        alexandria_root: str,
    ) -> OperationalBackupResult:
        managed_root = (vault_path / alexandria_root).resolve()
        if not managed_root.is_dir():
            raise BoundaryValidationError("canonical Vault root does not exist")
        if not self._operational_database_path.is_file():
            raise BoundaryValidationError("operational SQLite database does not exist")
        self._backup_root.mkdir(parents=True, exist_ok=True)
        if self._backup_root.is_symlink():
            raise BoundaryValidationError("operational backup root cannot be a symlink")
        backup_id = _backup_id()
        cipher = operational_backup_cipher(self._backup_root)
        final_root = self._backup_root / backup_id
        temporary_root = self._backup_root / f".{backup_id}.tmp"
        if final_root.exists() or temporary_root.exists():
            raise BoundaryValidationError("operational backup destination exists")
        temporary_root.mkdir()
        try:
            artifacts = _copy_canonical_vault(
                vault_path=vault_path,
                managed_root=managed_root,
                destination_root=temporary_root,
                cipher=cipher,
            )
            operational_destination = temporary_root / "sqlite/operational.sqlite"
            _backup_sqlite(
                source=self._operational_database_path,
                destination=operational_destination,
            )
            artifacts.append(
                _artifact(
                    kind="operational_database",
                    backup_root=temporary_root,
                    path=operational_destination,
                    cipher=cipher,
                )
            )
            checkpoint_source: str | None = None
            if self._librarian_checkpoint_path.is_file():
                checkpoint_destination = (
                    temporary_root / "sqlite/librarian-checkpoint.sqlite"
                )
                _backup_sqlite(
                    source=self._librarian_checkpoint_path,
                    destination=checkpoint_destination,
                )
                artifacts.append(
                    _artifact(
                        kind="librarian_checkpoint",
                        backup_root=temporary_root,
                        path=checkpoint_destination,
                        cipher=cipher,
                    )
                )
                checkpoint_source = str(self._librarian_checkpoint_path)
            manifest = OperationalBackupManifest(
                backup_id=backup_id,
                created_at=datetime.now(UTC),
                vault_source_path=str(vault_path),
                alexandria_root=alexandria_root,
                operational_database_source_path=str(self._operational_database_path),
                librarian_checkpoint_source_path=checkpoint_source,
                artifacts=sorted(
                    artifacts,
                    key=lambda item: (item.kind, item.relative_path),
                ),
            )
            manifest_path = temporary_root / _MANIFEST_NAME
            _write_json_atomic(
                manifest_path,
                manifest.model_dump(mode="json"),
            )
            _verify_manifest_files(temporary_root, manifest)
            os.replace(temporary_root, final_root)
            _prune_old_backups(
                backup_root=self._backup_root,
                retention_count=self._retention_count,
            )
            return OperationalBackupResult(
                backup_id=backup_id,
                backup_path=str(final_root),
                manifest_path=str(final_root / _MANIFEST_NAME),
                artifact_count=len(manifest.artifacts),
                total_bytes=manifest.total_bytes,
            )
        except BaseException:
            shutil.rmtree(temporary_root, ignore_errors=True)
            raise


def _copy_canonical_vault(
    *,
    vault_path: Path,
    managed_root: Path,
    destination_root: Path,
    cipher: Fernet,
) -> list[OperationalBackupArtifact]:
    artifacts: list[OperationalBackupArtifact] = []
    for source in sorted(managed_root.rglob("*")):
        if source.is_symlink():
            continue
        if not source.is_file():
            continue
        relative_to_vault = source.relative_to(vault_path)
        if (
            relative_to_vault.parts
            and relative_to_vault.parts[0] == _SYSTEM_VAULT_FOLDER
        ):
            continue
        destination = destination_root / "vault" / relative_to_vault
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)
        artifacts.append(
            _artifact(
                kind="canonical_vault",
                backup_root=destination_root,
                path=destination,
                cipher=cipher,
            )
        )
    return artifacts


def _backup_sqlite(*, source: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    source_uri = f"{source.as_uri()}?mode=ro"
    with (
        sqlite3.connect(source_uri, uri=True) as source_connection,
        sqlite3.connect(destination) as destination_connection,
    ):
        source_connection.backup(destination_connection)
        integrity = destination_connection.execute("PRAGMA integrity_check").fetchone()
    if integrity is None or integrity[0] != "ok":
        raise BoundaryValidationError("SQLite backup integrity check failed")


def _artifact(
    *,
    kind: Literal[
        "canonical_vault",
        "operational_database",
        "librarian_checkpoint",
    ],
    backup_root: Path,
    path: Path,
    cipher: Fernet,
) -> OperationalBackupArtifact:
    plaintext_sha256 = sha256_file(path)
    encrypted = cipher.encrypt(path.read_bytes())
    path.write_bytes(encrypted)
    return OperationalBackupArtifact(
        kind=kind,
        relative_path=path.relative_to(backup_root).as_posix(),
        sha256=sha256_file(path),
        size_bytes=path.stat().st_size,
        plaintext_sha256=plaintext_sha256,
    )


def operational_backup_cipher(backup_root: Path) -> Fernet:
    key_path = backup_root / _KEY_FILE_NAME
    if not key_path.exists():
        descriptor = os.open(
            key_path,
            os.O_WRONLY | os.O_CREAT | os.O_EXCL,
            0o600,
        )
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(Fernet.generate_key())
    if key_path.is_symlink():
        raise BoundaryValidationError("operational backup key cannot be a symlink")
    try:
        return Fernet(key_path.read_bytes())
    except (OSError, ValueError) as exc:
        raise BoundaryValidationError("operational backup key is invalid") from exc


def _prune_old_backups(*, backup_root: Path, retention_count: int) -> None:
    published = sorted(
        (
            path
            for path in backup_root.iterdir()
            if path.is_dir() and path.name.startswith("backup-")
        ),
        key=lambda path: path.name,
        reverse=True,
    )
    for expired in published[retention_count:]:
        shutil.rmtree(expired)


def _verify_manifest_files(
    backup_root: Path,
    manifest: OperationalBackupManifest,
) -> None:
    for item in manifest.artifacts:
        path = safe_backup_artifact_path(backup_root, item.relative_path)
        if not path.is_file():
            raise BoundaryValidationError("operational backup artifact is missing")
        if path.stat().st_size != item.size_bytes or sha256_file(path) != item.sha256:
            raise BoundaryValidationError("operational backup artifact hash mismatch")


def safe_backup_artifact_path(root: Path, relative_path: str) -> Path:
    relative = Path(relative_path)
    if relative.is_absolute() or ".." in relative.parts:
        raise BoundaryValidationError("operational backup artifact path is unsafe")
    candidate = (root / relative).resolve()
    if root not in candidate.parents:
        raise BoundaryValidationError("operational backup artifact escaped backup root")
    return candidate


def _write_json_atomic(path: Path, payload: JSONObject) -> None:
    temporary = path.with_suffix(f"{path.suffix}.tmp")
    temporary.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    os.replace(temporary, path)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _backup_id() -> str:
    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    return f"backup-{timestamp}-{uuid.uuid4().hex[:12]}"
