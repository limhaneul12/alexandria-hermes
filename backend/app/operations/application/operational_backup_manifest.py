"""Versioned manifest contract for portable operational backups."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from app.shared.schemas.common_schemas import StrictSchemaModel
from app.shared.schemas.datetime_schemas import AwareTimestamp


class OperationalBackupArtifact(StrictSchemaModel):
    """One hash-verified file stored under a backup directory."""

    kind: Literal["canonical_vault", "operational_database", "librarian_checkpoint"]
    relative_path: str
    sha256: str
    size_bytes: int
    plaintext_sha256: str


class OperationalBackupManifest(StrictSchemaModel):
    """Self-contained evidence needed to verify and restore one backup."""

    schema_version: Literal[2] = 2
    encryption: Literal["fernet"] = "fernet"
    backup_id: str
    created_at: AwareTimestamp
    vault_source_path: str
    alexandria_root: str
    operational_database_source_path: str
    librarian_checkpoint_source_path: str | None
    artifacts: list[OperationalBackupArtifact]

    @property
    def total_bytes(self) -> int:
        """Return the total content bytes represented by the manifest.

        Returns:
            Sum of all artifact sizes.
        """
        return sum(item.size_bytes for item in self.artifacts)

    @property
    def created_datetime(self) -> datetime:
        """Expose the validated aware timestamp as a datetime.

        Returns:
            Aware backup creation time.
        """
        return self.created_at
