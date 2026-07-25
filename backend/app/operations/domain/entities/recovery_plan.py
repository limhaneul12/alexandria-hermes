"""Recovery dry-run plan read models."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import datetime
from types import MappingProxyType

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
    markdown_manifest: Mapping[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Freeze the source manifest mapping."""
        object.__setattr__(
            self,
            "markdown_manifest",
            MappingProxyType(dict(self.markdown_manifest)),
        )


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
    diagnosis: tuple[str, ...]
    blocked_reasons: tuple[str, ...]
    source_snapshot: RecoverySourceSnapshot
    quarantine_artifacts: tuple[RecoveryQuarantineArtifactPlan, ...]
    steps: tuple[RecoveryPlanStep, ...]
    estimated_reindex_scope: Mapping[str, int | str | None]
    service_impact: tuple[str, ...]
    next_actions: tuple[str, ...]
    readiness: OperationalReadinessSnapshot
    warnings: tuple[str, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        """Normalize recovery plan collections to immutable values."""
        object.__setattr__(self, "diagnosis", tuple(self.diagnosis))
        object.__setattr__(self, "blocked_reasons", tuple(self.blocked_reasons))
        object.__setattr__(
            self, "quarantine_artifacts", tuple(self.quarantine_artifacts)
        )
        object.__setattr__(self, "steps", tuple(self.steps))
        object.__setattr__(
            self,
            "estimated_reindex_scope",
            MappingProxyType(dict(self.estimated_reindex_scope)),
        )
        object.__setattr__(self, "service_impact", tuple(self.service_impact))
        object.__setattr__(self, "next_actions", tuple(self.next_actions))
        object.__setattr__(self, "warnings", tuple(self.warnings))
