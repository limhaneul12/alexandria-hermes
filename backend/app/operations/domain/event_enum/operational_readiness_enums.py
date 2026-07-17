"""Operational readiness status values."""

from __future__ import annotations

from enum import StrEnum


class OperationalReadinessStatus(StrEnum):
    """Operational readiness states for knowledge retrieval safety."""

    UNKNOWN = "UNKNOWN"
    READY = "READY"
    DEGRADED_FTS_ONLY = "DEGRADED_FTS_ONLY"
    RECOVERY_REQUIRED = "RECOVERY_REQUIRED"
    RECOVERING = "RECOVERING"
    VERIFYING = "VERIFYING"
    BLOCKED = "BLOCKED"
    FAILED = "FAILED"
