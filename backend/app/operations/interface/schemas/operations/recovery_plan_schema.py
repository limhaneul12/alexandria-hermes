"""HTTP schemas for recovery dry-run planning."""

from __future__ import annotations

from pydantic import Field

from app.operations.application.recovery_plan_service import RecoveryPlanRequest
from app.operations.domain.entities.recovery_plan import (
    RecoveryPlan,
    RecoveryPlanStep,
    RecoveryQuarantineArtifactPlan,
    RecoverySourceSnapshot,
)
from app.operations.domain.event_enum.operational_readiness_enums import (
    OperationalReadinessStatus,
)
from app.operations.interface.schemas.operations.operational_readiness_schema import (
    OperationalReadinessSnapshotResponse,
)
from app.shared.schemas.common_schemas import StrictSchemaModel
from app.shared.schemas.datetime_schemas import AwareTimestamp


class RecoveryPlanRequestSchema(StrictSchemaModel):
    """Request schema for recovery dry-run planning."""

    trigger: str = Field(default="manual", min_length=1)
    actor: str = Field(default="operator", min_length=1)
    idempotency_key: str | None = Field(default=None, min_length=1)
    parent_run_id: str | None = Field(default=None, min_length=1)

    def to_contract(self) -> RecoveryPlanRequest:
        """Convert schema to application request contract.

        Returns:
            Recovery plan request contract.
        """
        return RecoveryPlanRequest(
            trigger=self.trigger,
            actor=self.actor,
            idempotency_key=self.idempotency_key,
            parent_run_id=self.parent_run_id,
        )


class RecoverySourceSnapshotResponse(StrictSchemaModel):
    """Source preservation preflight response."""

    vault_path: str
    alexandria_root: str
    managed_markdown_count: int
    representative_path: str | None
    representative_sha256: str | None
    disk_free_bytes: int | None
    access_error: str | None = None
    markdown_manifest: dict[str, str] = Field(default_factory=dict)

    @classmethod
    def from_entity(
        cls,
        snapshot: RecoverySourceSnapshot,
    ) -> RecoverySourceSnapshotResponse:
        """Create response schema from read model.

        Args:
            snapshot: Source snapshot read model.

        Returns:
            Source snapshot response schema.
        """
        return cls(
            vault_path=snapshot.vault_path,
            alexandria_root=snapshot.alexandria_root,
            managed_markdown_count=snapshot.managed_markdown_count,
            representative_path=snapshot.representative_path,
            representative_sha256=snapshot.representative_sha256,
            disk_free_bytes=snapshot.disk_free_bytes,
            access_error=snapshot.access_error,
            markdown_manifest=snapshot.markdown_manifest,
        )


class RecoveryQuarantineArtifactPlanResponse(StrictSchemaModel):
    """Planned SQLite quarantine artifact response."""

    source_path: str
    quarantine_path: str
    exists: bool
    size_bytes: int | None
    sha256: str | None

    @classmethod
    def from_entity(
        cls,
        artifact: RecoveryQuarantineArtifactPlan,
    ) -> RecoveryQuarantineArtifactPlanResponse:
        """Create response schema from read model.

        Args:
            artifact: Quarantine artifact read model.

        Returns:
            Quarantine artifact response schema.
        """
        return cls(
            source_path=artifact.source_path,
            quarantine_path=artifact.quarantine_path,
            exists=artifact.exists,
            size_bytes=artifact.size_bytes,
            sha256=artifact.sha256,
        )


class RecoveryPlanStepResponse(StrictSchemaModel):
    """Planned recovery step response."""

    code: str
    title: str
    mutates_state: bool

    @classmethod
    def from_entity(cls, step: RecoveryPlanStep) -> RecoveryPlanStepResponse:
        """Create response schema from read model.

        Args:
            step: Recovery step read model.

        Returns:
            Recovery step response schema.
        """
        return cls(code=step.code, title=step.title, mutates_state=step.mutates_state)


class RecoveryPlanResponse(StrictSchemaModel):
    """Recovery dry-run plan response."""

    id: str
    parent_run_id: str | None
    idempotency_key: str
    trigger: str
    actor: str
    status: OperationalReadinessStatus
    created_at: AwareTimestamp
    target_database_path: str | None
    dry_run: bool
    deletion_performed: bool
    automatic_execution_allowed: bool
    diagnosis: list[str] = Field(default_factory=list)
    blocked_reasons: list[str] = Field(default_factory=list)
    source_snapshot: RecoverySourceSnapshotResponse
    quarantine_artifacts: list[RecoveryQuarantineArtifactPlanResponse] = Field(
        default_factory=list
    )
    steps: list[RecoveryPlanStepResponse] = Field(default_factory=list)
    estimated_reindex_scope: dict[str, int | str | None]
    service_impact: list[str] = Field(default_factory=list)
    next_actions: list[str] = Field(default_factory=list)
    readiness: OperationalReadinessSnapshotResponse
    warnings: list[str] = Field(default_factory=list)

    @classmethod
    def from_entity(cls, plan: RecoveryPlan) -> RecoveryPlanResponse:
        """Create response schema from read model.

        Args:
            plan: Recovery dry-run plan.

        Returns:
            Recovery plan response schema.
        """
        return cls(
            id=plan.id,
            parent_run_id=plan.parent_run_id,
            idempotency_key=plan.idempotency_key,
            trigger=plan.trigger,
            actor=plan.actor,
            status=plan.status,
            created_at=plan.created_at,
            target_database_path=plan.target_database_path,
            dry_run=plan.dry_run,
            deletion_performed=plan.deletion_performed,
            automatic_execution_allowed=plan.automatic_execution_allowed,
            diagnosis=plan.diagnosis,
            blocked_reasons=plan.blocked_reasons,
            source_snapshot=RecoverySourceSnapshotResponse.from_entity(
                plan.source_snapshot
            ),
            quarantine_artifacts=[
                RecoveryQuarantineArtifactPlanResponse.from_entity(artifact)
                for artifact in plan.quarantine_artifacts
            ],
            steps=[RecoveryPlanStepResponse.from_entity(step) for step in plan.steps],
            estimated_reindex_scope=plan.estimated_reindex_scope,
            service_impact=plan.service_impact,
            next_actions=plan.next_actions,
            readiness=OperationalReadinessSnapshotResponse.from_entity(plan.readiness),
            warnings=plan.warnings,
        )
