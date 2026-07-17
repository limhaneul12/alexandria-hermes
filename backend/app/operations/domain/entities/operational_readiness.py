"""Operational readiness read models."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from app.memory.domain.entities.context_read_models import ContextEmbeddingSourceStatus
from app.memory.domain.event_enum.context_enums import RagHealthState, RagStrategy
from app.operations.domain.event_enum.operational_readiness_enums import (
    OperationalReadinessStatus,
)
from app.shared.types.extra_types import JSONObject


@dataclass(frozen=True, slots=True)
class OperationalVaultSnapshot:
    """Vault and index state used by operational readiness."""

    exists: bool
    readable: bool
    vault_path: str
    alexandria_root: str
    alexandria_root_exists: bool
    indexed_notes: int
    stale_notes: int
    error_notes: int


@dataclass(frozen=True, slots=True)
class OperationalDatabaseSnapshot:
    """Database state used by operational readiness."""

    reachable: bool
    integrity: str
    schema_version: str | None
    corruption_detected: bool = False


@dataclass(frozen=True, slots=True)
class OperationalRagSnapshot:
    """RAG state used by operational readiness."""

    fts: RagHealthState
    vector: RagHealthState
    embedding: RagHealthState
    effective_strategy: RagStrategy
    model_name: str
    dimensions: int
    fingerprint: JSONObject | None
    source_statuses: list[ContextEmbeddingSourceStatus] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


@dataclass(frozen=True, slots=True)
class OperationalReadinessSnapshot:
    """Read-only operational readiness snapshot."""

    status: OperationalReadinessStatus
    ready: bool
    checked_at: datetime
    duration_ms: int
    vault: OperationalVaultSnapshot
    database: OperationalDatabaseSnapshot
    rag: OperationalRagSnapshot
    active_recovery_run_id: str | None
    last_successful_recovery_run_id: str | None
    warnings: list[str]
    blockers: list[str]
    next_actions: list[str]
