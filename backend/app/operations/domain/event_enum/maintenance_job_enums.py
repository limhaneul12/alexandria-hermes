"""Redis-backed maintenance job lifecycle enums."""

from __future__ import annotations

from enum import StrEnum


class MaintenanceJobKind(StrEnum):
    """Maintenance operations accepted by the bounded worker."""

    EMBEDDING_REINDEX = "embedding_reindex"


class MaintenanceJobStatus(StrEnum):
    """Observable lifecycle states for one maintenance job."""

    QUEUED = "QUEUED"
    RUNNING = "RUNNING"
    RETRYING = "RETRYING"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"
