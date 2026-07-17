"""HTTP schemas for recovery run execution."""

from __future__ import annotations

from pydantic import Field

from app.operations.application.recovery_plan_service import RecoveryPlanRequest
from app.operations.domain.entities.recovery_run import (
    RecoveryQuarantineInventoryItem,
    RecoveryRun,
    RecoveryRunStepResult,
)
from app.operations.domain.event_enum.operational_recovery_enums import (
    RecoveryRunStatus,
    RecoveryStepStatus,
)
from app.operations.interface.schemas.operations.recovery_plan_schema import (
    RecoveryPlanRequestSchema,
    RecoveryPlanStepResponse,
    RecoveryQuarantineArtifactPlanResponse,
    RecoverySourceSnapshotResponse,
)
from app.shared.schemas.common_schemas import StrictSchemaModel
from app.shared.schemas.datetime_schemas import AwareTimestamp
from app.shared.types.extra_types import JSONObject


class RecoveryRunRequestSchema(RecoveryPlanRequestSchema):
    """Request schema for starting a recovery run."""

    def to_contract(self) -> RecoveryPlanRequest:
        """Convert schema to application request contract.

        Returns:
            Recovery plan/start request contract.
        """
        return RecoveryPlanRequest(
            trigger=self.trigger,
            actor=self.actor,
            idempotency_key=self.idempotency_key,
            parent_run_id=self.parent_run_id,
        )


class RecoveryRunRetryRequestSchema(RecoveryRunRequestSchema):
    """Request schema for retrying a recovery run."""

    trigger: str = Field(default="retry", min_length=1)
    parent_run_id: None = None

    def to_contract(self) -> RecoveryPlanRequest:
        """Convert schema to application retry contract.

        Returns:
            Recovery retry request contract.
        """
        return RecoveryPlanRequest(
            trigger=self.trigger,
            actor=self.actor,
            idempotency_key=self.idempotency_key,
            parent_run_id=None,
        )


class RecoveryRunStepResultResponse(StrictSchemaModel):
    """Recovery step execution result response."""

    code: str
    status: RecoveryStepStatus
    attempts: int
    started_at: AwareTimestamp | None
    finished_at: AwareTimestamp | None
    input_hash: str
    result: JSONObject = Field(default_factory=dict)

    @classmethod
    def from_entity(
        cls,
        step: RecoveryRunStepResult,
    ) -> RecoveryRunStepResultResponse:
        """Create response schema from read model.

        Args:
            step: Recovery step execution result.

        Returns:
            Step result response schema.
        """
        return cls(
            code=step.code,
            status=step.status,
            attempts=step.attempts,
            started_at=step.started_at,
            finished_at=step.finished_at,
            input_hash=step.input_hash,
            result=step.result,
        )


class RecoveryRunResponse(StrictSchemaModel):
    """Recovery run response."""

    id: str
    parent_run_id: str | None
    idempotency_key: str
    trigger: str
    actor: str
    status: RecoveryRunStatus
    current_step: str | None
    started_at: AwareTimestamp
    updated_at: AwareTimestamp
    finished_at: AwareTimestamp | None
    source_snapshot: RecoverySourceSnapshotResponse
    diagnosis: list[str] = Field(default_factory=list)
    quarantine_artifacts: list[RecoveryQuarantineArtifactPlanResponse] = Field(
        default_factory=list
    )
    planned_steps: list[RecoveryPlanStepResponse] = Field(default_factory=list)
    step_results: list[RecoveryRunStepResultResponse] = Field(default_factory=list)
    rebuild_results: JSONObject = Field(default_factory=dict)
    verification_results: JSONObject = Field(default_factory=dict)
    error_code: str | None
    error_summary: str | None
    next_actions: list[str] = Field(default_factory=list)
    manifest_path: str

    @classmethod
    def from_entity(cls, run: RecoveryRun) -> RecoveryRunResponse:
        """Create response schema from read model.

        Args:
            run: Recovery run read model.

        Returns:
            Recovery run response schema.
        """
        return cls(
            id=run.id,
            parent_run_id=run.parent_run_id,
            idempotency_key=run.idempotency_key,
            trigger=run.trigger,
            actor=run.actor,
            status=run.status,
            current_step=run.current_step,
            started_at=run.started_at,
            updated_at=run.updated_at,
            finished_at=run.finished_at,
            source_snapshot=RecoverySourceSnapshotResponse.from_entity(
                run.source_snapshot
            ),
            diagnosis=run.diagnosis,
            quarantine_artifacts=[
                RecoveryQuarantineArtifactPlanResponse.from_entity(artifact)
                for artifact in run.quarantine_artifacts
            ],
            planned_steps=[
                RecoveryPlanStepResponse.from_entity(step) for step in run.planned_steps
            ],
            step_results=[
                RecoveryRunStepResultResponse.from_entity(step)
                for step in run.step_results
            ],
            rebuild_results=run.rebuild_results,
            verification_results=run.verification_results,
            error_code=run.error_code,
            error_summary=run.error_summary,
            next_actions=run.next_actions,
            manifest_path=run.manifest_path,
        )


class RecoveryQuarantineInventoryItemResponse(StrictSchemaModel):
    """One quarantined recovery artifact inventory item."""

    run_id: str
    run_status: RecoveryRunStatus
    source_path: str
    quarantine_path: str
    exists: bool
    size_bytes: int | None
    sha256: str | None

    @classmethod
    def from_entity(
        cls,
        item: RecoveryQuarantineInventoryItem,
    ) -> RecoveryQuarantineInventoryItemResponse:
        """Create response schema from read model.

        Args:
            item: Quarantine inventory item.

        Returns:
            Quarantine inventory item response schema.
        """
        return cls(
            run_id=item.run_id,
            run_status=item.run_status,
            source_path=item.source_path,
            quarantine_path=item.quarantine_path,
            exists=item.exists,
            size_bytes=item.size_bytes,
            sha256=item.sha256,
        )


class RecoveryQuarantineInventoryResponse(StrictSchemaModel):
    """Quarantine inventory response."""

    items: list[RecoveryQuarantineInventoryItemResponse] = Field(default_factory=list)
    total: int

    @classmethod
    def from_entities(
        cls,
        items: list[RecoveryQuarantineInventoryItem],
    ) -> RecoveryQuarantineInventoryResponse:
        """Create response schema from inventory read models.

        Args:
            items: Quarantine inventory items.

        Returns:
            Quarantine inventory response schema.
        """
        response_items = [
            RecoveryQuarantineInventoryItemResponse.from_entity(item) for item in items
        ]
        return cls(items=response_items, total=len(response_items))
