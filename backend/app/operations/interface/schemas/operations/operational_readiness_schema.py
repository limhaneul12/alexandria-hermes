"""HTTP schemas for operational readiness."""

from __future__ import annotations

from pydantic import Field

from app.memory.interface.schemas.context.context_mapping import source_status_payload
from app.memory.interface.schemas.context.context_schema import (
    ContextEmbeddingSourceStatusResponse,
)
from app.operations.domain.entities.operational_readiness import (
    OperationalDatabaseSnapshot,
    OperationalRagSnapshot,
    OperationalReadinessSnapshot,
    OperationalVaultSnapshot,
)
from app.operations.domain.event_enum.operational_readiness_enums import (
    OperationalReadinessStatus,
)
from app.shared.schemas.common_schemas import StrictSchemaModel
from app.shared.schemas.datetime_schemas import AwareTimestamp
from app.shared.types.extra_types import JSONObject


class OperationalVaultSnapshotResponse(StrictSchemaModel):
    """Vault state in the operational readiness response."""

    exists: bool
    readable: bool
    vault_path: str
    alexandria_root: str
    alexandria_root_exists: bool
    indexed_notes: int
    stale_notes: int
    error_notes: int

    @classmethod
    def from_entity(
        cls,
        snapshot: OperationalVaultSnapshot,
    ) -> OperationalVaultSnapshotResponse:
        """Create response schema from read model.

        Args:
            snapshot: Vault readiness read model.

        Returns:
            Vault response schema.
        """
        return cls(
            exists=snapshot.exists,
            readable=snapshot.readable,
            vault_path=snapshot.vault_path,
            alexandria_root=snapshot.alexandria_root,
            alexandria_root_exists=snapshot.alexandria_root_exists,
            indexed_notes=snapshot.indexed_notes,
            stale_notes=snapshot.stale_notes,
            error_notes=snapshot.error_notes,
        )


class OperationalDatabaseSnapshotResponse(StrictSchemaModel):
    """Database state in the operational readiness response."""

    reachable: bool
    integrity: str
    schema_version: str | None
    corruption_detected: bool = False

    @classmethod
    def from_entity(
        cls,
        snapshot: OperationalDatabaseSnapshot,
    ) -> OperationalDatabaseSnapshotResponse:
        """Create response schema from read model.

        Args:
            snapshot: Database readiness read model.

        Returns:
            Database response schema.
        """
        return cls(
            reachable=snapshot.reachable,
            integrity=snapshot.integrity,
            schema_version=snapshot.schema_version,
            corruption_detected=snapshot.corruption_detected,
        )


class OperationalRagSnapshotResponse(StrictSchemaModel):
    """RAG state in the operational readiness response."""

    fts: str
    vector: str
    embedding: str
    effective_strategy: str
    model_name: str
    dimensions: int
    fingerprint: JSONObject | None
    source_statuses: list[ContextEmbeddingSourceStatusResponse] = Field(
        default_factory=list
    )
    warnings: list[str] = Field(default_factory=list)

    @classmethod
    def from_entity(
        cls,
        snapshot: OperationalRagSnapshot,
    ) -> OperationalRagSnapshotResponse:
        """Create response schema from read model.

        Args:
            snapshot: RAG readiness read model.

        Returns:
            RAG response schema.
        """
        return cls(
            fts=snapshot.fts.value,
            vector=snapshot.vector.value,
            embedding=snapshot.embedding.value,
            effective_strategy=snapshot.effective_strategy.value,
            model_name=snapshot.model_name,
            dimensions=snapshot.dimensions,
            fingerprint=snapshot.fingerprint,
            source_statuses=[
                ContextEmbeddingSourceStatusResponse.model_validate(
                    source_status_payload(status)
                )
                for status in snapshot.source_statuses
            ],
            warnings=snapshot.warnings,
        )


class OperationalReadinessSnapshotResponse(StrictSchemaModel):
    """Read-only operational readiness response."""

    status: OperationalReadinessStatus
    ready: bool
    checked_at: AwareTimestamp
    duration_ms: int
    vault: OperationalVaultSnapshotResponse
    database: OperationalDatabaseSnapshotResponse
    rag: OperationalRagSnapshotResponse
    active_recovery_run_id: str | None = None
    last_successful_recovery_run_id: str | None = None
    warnings: list[str] = Field(default_factory=list)
    blockers: list[str] = Field(default_factory=list)
    next_actions: list[str] = Field(default_factory=list)

    @classmethod
    def from_entity(
        cls,
        snapshot: OperationalReadinessSnapshot,
    ) -> OperationalReadinessSnapshotResponse:
        """Create response schema from read model.

        Args:
            snapshot: Operational readiness read model.

        Returns:
            Operational readiness response schema.
        """
        return cls(
            status=snapshot.status,
            ready=snapshot.ready,
            checked_at=snapshot.checked_at,
            duration_ms=snapshot.duration_ms,
            vault=OperationalVaultSnapshotResponse.from_entity(snapshot.vault),
            database=OperationalDatabaseSnapshotResponse.from_entity(snapshot.database),
            rag=OperationalRagSnapshotResponse.from_entity(snapshot.rag),
            active_recovery_run_id=snapshot.active_recovery_run_id,
            last_successful_recovery_run_id=snapshot.last_successful_recovery_run_id,
            warnings=snapshot.warnings,
            blockers=snapshot.blockers,
            next_actions=snapshot.next_actions,
        )
