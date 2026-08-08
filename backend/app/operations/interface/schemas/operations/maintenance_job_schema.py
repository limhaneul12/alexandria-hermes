"""HTTP schemas for Redis-backed maintenance jobs."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.operations.domain.entities.maintenance_job import (
    EmbeddingReindexJobResult,
    MaintenanceJobSnapshot,
    MaintenanceQueueSnapshot,
)
from app.operations.domain.event_enum.maintenance_job_enums import (
    MaintenanceJobKind,
    MaintenanceJobStatus,
)


class EmbeddingReindexJobRequest(BaseModel):
    """Submit one bounded embedding reindex operation."""

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        validate_default=True,
    )

    requested_by: str = Field(default="manual", min_length=1, max_length=120)
    source_id: str = Field(default="manual", min_length=1, max_length=200)
    limit: int = Field(default=250, ge=1, le=1000)
    force: bool = False


class EmbeddingReindexJobResultResponse(BaseModel):
    """Bounded embedding batch result."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    scanned: int
    updated: int
    skipped: int
    warnings: tuple[str, ...] = ()

    @classmethod
    def from_entity(
        cls,
        result: EmbeddingReindexJobResult,
    ) -> EmbeddingReindexJobResultResponse:
        return cls(
            scanned=result.scanned,
            updated=result.updated,
            skipped=result.skipped,
            warnings=result.warnings,
        )


class MaintenanceJobResponse(BaseModel):
    """Operator-visible queued maintenance lifecycle state."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    job_id: str
    kind: MaintenanceJobKind
    status: MaintenanceJobStatus
    requested_by: str
    source_id: str
    limit: int
    force: bool
    attempts: int
    submitted_at: datetime
    started_at: datetime | None = None
    finished_at: datetime | None = None
    stream_id: str | None = None
    deduplicated: bool = False
    error_summary: str | None = None
    result: EmbeddingReindexJobResultResponse | None = None

    @classmethod
    def from_entity(cls, snapshot: MaintenanceJobSnapshot) -> MaintenanceJobResponse:
        """Map an immutable domain snapshot to the HTTP response.

        Args:
            snapshot: Immutable maintenance job domain snapshot.

        Returns:
            Validated operator-visible maintenance job response model.
        """
        result = snapshot.result
        return cls(
            job_id=snapshot.job_id,
            kind=snapshot.kind,
            status=snapshot.status,
            requested_by=snapshot.requested_by,
            source_id=snapshot.source_id,
            limit=snapshot.limit,
            force=snapshot.force,
            attempts=snapshot.attempts,
            submitted_at=snapshot.submitted_at,
            started_at=snapshot.started_at,
            finished_at=snapshot.finished_at,
            stream_id=snapshot.stream_id,
            deduplicated=snapshot.deduplicated,
            error_summary=snapshot.error_summary,
            result=(
                None
                if result is None
                else EmbeddingReindexJobResultResponse.from_entity(result)
            ),
        )


class MaintenanceQueueStatusResponse(BaseModel):
    """Bounded Redis Streams backlog and worker evidence."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    stream_length: int
    pending: int
    consumers: int
    dead_letter_length: int

    @classmethod
    def from_entity(
        cls,
        snapshot: MaintenanceQueueSnapshot,
    ) -> MaintenanceQueueStatusResponse:
        return cls(
            stream_length=snapshot.stream_length,
            pending=snapshot.pending,
            consumers=snapshot.consumers,
            dead_letter_length=snapshot.dead_letter_length,
        )
