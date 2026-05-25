"""Skill artifact enum definitions."""

from __future__ import annotations

from enum import StrEnum


class RiskLevel(StrEnum):
    """Skill risk level classification."""

    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
