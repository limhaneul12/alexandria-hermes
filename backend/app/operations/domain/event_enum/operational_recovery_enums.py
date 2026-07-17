"""Operational recovery run status values."""

from __future__ import annotations

from enum import StrEnum


class RecoveryRunStatus(StrEnum):
    """Recovery run lifecycle states."""

    PLANNED = "PLANNED"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    BLOCKED = "BLOCKED"
    FAILED = "FAILED"


class RecoveryStepStatus(StrEnum):
    """Recovery step lifecycle states."""

    PENDING = "PENDING"
    RUNNING = "RUNNING"
    SUCCEEDED = "SUCCEEDED"
    SKIPPED = "SKIPPED"
    BLOCKED = "BLOCKED"
    FAILED = "FAILED"
