"""Memory Compact enum definitions."""

from __future__ import annotations

from enum import StrEnum


class MemoryCompactStatus(StrEnum):
    """Lifecycle status for durable memory compact artifacts."""

    DRAFT = "DRAFT"
    CURRENT = "CURRENT"
    SUPERSEDED = "SUPERSEDED"
    ARCHIVED = "ARCHIVED"


class MemoryCompactReviewVerdict(StrEnum):
    """Librarian review verdict for Memory Compact quality gates."""

    PASS = "pass"
    NEEDS_REVISION = "needs_revision"
    BLOCKED = "blocked"
