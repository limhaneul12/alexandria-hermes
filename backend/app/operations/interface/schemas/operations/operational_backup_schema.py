"""HTTP schemas for local operational backup and restore drills."""

from __future__ import annotations

from app.operations.application.operational_state_backup_service import (
    OperationalBackupResult,
)
from app.operations.application.operational_state_restore_service import (
    OperationalRestoreDrillResult,
)
from app.shared.schemas.common_schemas import StrictSchemaModel


class OperationalBackupResponse(StrictSchemaModel):
    """Published operational backup evidence."""

    backup_id: str
    backup_path: str
    manifest_path: str
    artifact_count: int
    total_bytes: int

    @classmethod
    def from_entity(cls, result: OperationalBackupResult) -> OperationalBackupResponse:
        return cls(
            backup_id=result.backup_id,
            backup_path=result.backup_path,
            manifest_path=result.manifest_path,
            artifact_count=result.artifact_count,
            total_bytes=result.total_bytes,
        )


class OperationalRestoreDrillResponse(StrictSchemaModel):
    """Non-destructive isolated restore drill evidence."""

    backup_id: str
    drill_id: str
    restore_path: str
    verified_artifacts: int
    total_bytes: int
    sqlite_integrity: str

    @classmethod
    def from_entity(
        cls,
        result: OperationalRestoreDrillResult,
    ) -> OperationalRestoreDrillResponse:
        return cls(
            backup_id=result.backup_id,
            drill_id=result.drill_id,
            restore_path=result.restore_path,
            verified_artifacts=result.verified_artifacts,
            total_bytes=result.total_bytes,
            sqlite_integrity=result.sqlite_integrity,
        )
