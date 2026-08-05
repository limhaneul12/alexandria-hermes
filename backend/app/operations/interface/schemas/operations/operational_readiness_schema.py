"""HTTP schemas for operational readiness."""

from __future__ import annotations

from pydantic import Field

from app.memory.interface.schemas.context.context_mapping import source_status_payload
from app.memory.interface.schemas.context.context_schema import (
    ContextEmbeddingSourceStatusResponse,
)
from app.operations.application.operational_overall_readiness import (
    overall_readiness_status,
)
from app.operations.domain.entities.operational_data_integrity import (
    OperationalDataIntegritySnapshot,
)
from app.operations.domain.entities.operational_readiness import (
    OperationalDatabaseSnapshot,
    OperationalRagSnapshot,
    OperationalReadinessSnapshot,
    OperationalReconciliationSnapshot,
    OperationalVaultSnapshot,
)
from app.operations.domain.event_enum.operational_data_integrity_enums import (
    OperationalDataIntegrityStatus,
    OperationalDataIntegrityWarningCode,
)
from app.operations.domain.event_enum.operational_readiness_enums import (
    OperationalOverallStatus,
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
            warnings=list(snapshot.warnings),
        )


class OperationalReconciliationSnapshotResponse(StrictSchemaModel):
    """Memory reconciliation state in the operational readiness response."""

    configured: bool
    reachable: bool
    total_contexts: int
    temporal_state_count: int
    missing_temporal_states: int
    backfill_complete: bool
    total_plans: int
    pending_review_plans: int
    total_results: int
    partial_apply_results: int
    failed_results: int
    open_conflicts: int
    reviewing_conflicts: int
    hard_delete_results: int
    latest_failure_code: str | None
    latest_failure_at: AwareTimestamp | None

    @classmethod
    def from_entity(
        cls,
        snapshot: OperationalReconciliationSnapshot,
    ) -> OperationalReconciliationSnapshotResponse:
        """Create response schema from reconciliation readiness state.

        Args:
            snapshot: Snapshot.

        Returns:
            OperationalReconciliationSnapshotResponse: Operation result.
        """
        return cls(
            configured=snapshot.configured,
            reachable=snapshot.reachable,
            total_contexts=snapshot.total_contexts,
            temporal_state_count=snapshot.temporal_state_count,
            missing_temporal_states=snapshot.missing_temporal_states,
            backfill_complete=snapshot.backfill_complete,
            total_plans=snapshot.total_plans,
            pending_review_plans=snapshot.pending_review_plans,
            total_results=snapshot.total_results,
            partial_apply_results=snapshot.partial_apply_results,
            failed_results=snapshot.failed_results,
            open_conflicts=snapshot.open_conflicts,
            reviewing_conflicts=snapshot.reviewing_conflicts,
            hard_delete_results=snapshot.hard_delete_results,
            latest_failure_code=snapshot.latest_failure_code,
            latest_failure_at=snapshot.latest_failure_at,
        )


class OperationalDataIntegrityWarningResponse(StrictSchemaModel):
    """One aggregated canonical-data warning."""

    code: OperationalDataIntegrityWarningCode
    count: int
    note_paths: list[str] = Field(default_factory=list)
    fields: list[str] = Field(default_factory=list)


class OperationalDataIntegritySnapshotResponse(StrictSchemaModel):
    """Canonical managed-note integrity independent of infrastructure."""

    status: OperationalDataIntegrityStatus = OperationalDataIntegrityStatus.NOT_CHECKED
    scanned_notes: int = 0
    warnings: list[OperationalDataIntegrityWarningResponse] = Field(
        default_factory=list
    )

    @classmethod
    def from_entity(
        cls,
        snapshot: OperationalDataIntegritySnapshot,
    ) -> OperationalDataIntegritySnapshotResponse:
        """Map the internal integrity snapshot to the HTTP contract.

        Args:
            snapshot: Internal data-integrity diagnostic snapshot.

        Returns:
            HTTP data-integrity response.
        """
        return cls(
            status=snapshot.status,
            scanned_notes=snapshot.scanned_notes,
            warnings=[
                OperationalDataIntegrityWarningResponse(
                    code=warning.code,
                    count=warning.count,
                    note_paths=list(warning.note_paths),
                    fields=list(warning.fields),
                )
                for warning in snapshot.warnings
            ],
        )


class OperationalReadinessSnapshotResponse(StrictSchemaModel):
    """Read-only operational readiness response."""

    status: OperationalReadinessStatus
    overall_status: OperationalOverallStatus
    ready: bool
    checked_at: AwareTimestamp
    duration_ms: int
    vault: OperationalVaultSnapshotResponse
    database: OperationalDatabaseSnapshotResponse
    rag: OperationalRagSnapshotResponse
    reconciliation: OperationalReconciliationSnapshotResponse
    active_recovery_run_id: str | None = None
    last_successful_recovery_run_id: str | None = None
    warnings: list[str] = Field(default_factory=list)
    blockers: list[str] = Field(default_factory=list)
    next_actions: list[str] = Field(default_factory=list)
    data_integrity: OperationalDataIntegritySnapshotResponse = Field(
        default_factory=OperationalDataIntegritySnapshotResponse
    )

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
            overall_status=overall_readiness_status(snapshot),
            ready=snapshot.ready,
            checked_at=snapshot.checked_at,
            duration_ms=snapshot.duration_ms,
            vault=OperationalVaultSnapshotResponse.from_entity(snapshot.vault),
            database=OperationalDatabaseSnapshotResponse.from_entity(snapshot.database),
            rag=OperationalRagSnapshotResponse.from_entity(snapshot.rag),
            reconciliation=OperationalReconciliationSnapshotResponse.from_entity(
                snapshot.reconciliation
            ),
            active_recovery_run_id=snapshot.active_recovery_run_id,
            last_successful_recovery_run_id=snapshot.last_successful_recovery_run_id,
            warnings=list(snapshot.warnings),
            blockers=list(snapshot.blockers),
            next_actions=list(snapshot.next_actions),
            data_integrity=OperationalDataIntegritySnapshotResponse.from_entity(
                snapshot.data_integrity
            ),
        )
