"""Independent readiness states for core and optional platform capabilities."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum


class OperationalCapabilityState(StrEnum):
    """One capability's independent serving state."""

    READY = "READY"
    DEGRADED = "DEGRADED"
    BLOCKED = "BLOCKED"
    OPTIONAL = "OPTIONAL"


@dataclass(frozen=True, slots=True)
class OperationalCapability:
    """Readiness and findings for one independently usable capability."""

    state: OperationalCapabilityState
    ready: bool
    blockers: tuple[str, ...]
    warnings: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class OperationalCapabilitySnapshot:
    """Core memory is assessed independently from semantic and Librarian layers."""

    checked_at: datetime
    core_memory: OperationalCapability
    semantic_retrieval: OperationalCapability
    librarian: OperationalCapability
