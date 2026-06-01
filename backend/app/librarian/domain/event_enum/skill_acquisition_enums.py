"""Skill-acquisition artifact enum definitions."""

from __future__ import annotations

from enum import StrEnum


class ItemStatus(StrEnum):
    """Publication state for a generated skill artifact."""

    DRAFT = "DRAFT"
    NEEDS_REVIEW = "NEEDS_REVIEW"
    ACTIVE = "ACTIVE"
    ARCHIVED = "ARCHIVED"
    DEPRECATED = "DEPRECATED"
    SUPERSEDED = "SUPERSEDED"


class RiskLevel(StrEnum):
    """Skill risk level classification."""

    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
