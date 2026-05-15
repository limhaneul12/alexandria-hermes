"""Workflow concept enum definitions."""

from __future__ import annotations

from enum import StrEnum


class WorkflowDetailField(StrEnum):
    """Workflow details keys accepted by public patch payloads."""

    STEPS = "steps"
    RELATED_SKILL_IDS = "related_skill_ids"
    EXPECTED_RESULT = "expected_result"
    USE_CASE = "use_case"
