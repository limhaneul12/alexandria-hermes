"""Recovery dry-run plan read models."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from app.operations.domain.entities.operational_readiness import (
    OperationalReadinessSnapshot,
)
from app.operations.domain.event_enum.operational_readiness_enums import (
    OperationalReadinessStatus,
)


@dataclass(frozen=True, slots=True)
class RecoverySourceSnapshot:
    """Read-only source preservation preflight evidence."""

    vault_path: str
    alexandria_root: str
    managed_markdown_count: int
    representative_path: str | None
    representative_sha256: str | None
    disk_free_bytes: int | None
    access_error: str | None = None
    markdown_manifest: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class RecoveryQuarantineArtifactPlan:
    """Planned quarantine move for one SQLite file."""

    source_path: str
    quarantine_path: str
    exists: bool
    size_bytes: int | None
    sha256: str | None


@dataclass(frozen=True, slots=True)
class RecoveryPlanStep:
    """One planned recovery step."""

    code: str
    title: str
    mutates_state: bool


@dataclass(frozen=True, slots=True)
class RecoveryPlan:
    """Read-only recovery dry-run plan."""

    id: str
    parent_run_id: str | None
    idempotency_key: str
    trigger: str
    actor: str
    status: OperationalReadinessStatus
    created_at: datetime
    target_database_path: str | None
    dry_run: bool
    deletion_performed: bool
    automatic_execution_allowed: bool
    diagnosis: list[str]
    blocked_reasons: list[str]
    source_snapshot: RecoverySourceSnapshot
    quarantine_artifacts: list[RecoveryQuarantineArtifactPlan]
    steps: list[RecoveryPlanStep]
    estimated_reindex_scope: dict[str, int | str | None]
    service_impact: list[str]
    next_actions: list[str]
    readiness: OperationalReadinessSnapshot
    warnings: list[str] = field(default_factory=list)
