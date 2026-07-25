"""Vault snapshot, file hashing, and quarantine artifact planning."""

from __future__ import annotations

from datetime import datetime
from hashlib import sha256
from pathlib import Path
from shutil import disk_usage
from typing import Protocol

from app.operations.domain.entities.recovery_plan import (
    RecoveryQuarantineArtifactPlan,
    RecoverySourceSnapshot,
)


class DiskUsageSnapshot(Protocol):
    """Filesystem capacity values required by recovery source planning."""

    @property
    def free(self) -> int:
        """Return free filesystem bytes.

        Returns:
            Available filesystem bytes.
        """


class DiskUsageProvider(Protocol):
    """Callable boundary for filesystem capacity inspection."""

    def __call__(self, path: Path) -> DiskUsageSnapshot:
        """Return capacity values for one filesystem path.

        Args:
            path: Filesystem path whose capacity should be inspected.

        Returns:
            Filesystem capacity values.
        """


def _source_snapshot(
    *,
    vault_path: str,
    alexandria_root: str,
    disk_usage_provider: DiskUsageProvider = disk_usage,
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
            free_bytes = disk_usage_provider(root).free
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
