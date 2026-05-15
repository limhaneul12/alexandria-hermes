"""Skill concept enum definitions."""

from __future__ import annotations

from enum import StrEnum


class RiskLevel(StrEnum):
    """Skill risk level classification."""

    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class SkillAcquisitionMethod(StrEnum):
    """How an agent obtained a skill candidate."""

    SELF_ACQUISITION = "SELF_ACQUISITION"


class SkillCandidateHarnessStatus(StrEnum):
    """Validation status for agent-authored skill candidates."""

    PASSED = "PASSED"
    NEEDS_REVIEW = "NEEDS_REVIEW"


class SkillDetailField(StrEnum):
    """Skill details keys accepted by public patch payloads."""

    PURPOSE = "purpose"
    INPUT_SCHEMA = "input_schema"
    OUTPUT_SCHEMA = "output_schema"
    USAGE_EXAMPLE = "usage_example"
    REQUIRED_TOOLS = "required_tools"
    RISK_LEVEL = "risk_level"
    VERSION = "version"
