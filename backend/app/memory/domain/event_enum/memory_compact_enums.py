"""Memory Compact enum definitions."""

from __future__ import annotations

from enum import StrEnum


class MemoryCompactStatus(StrEnum):
    """Lifecycle status for durable memory compact artifacts."""

    DRAFT = "DRAFT"
    CURRENT = "CURRENT"
    SUPERSEDED = "SUPERSEDED"
    ARCHIVED = "ARCHIVED"
