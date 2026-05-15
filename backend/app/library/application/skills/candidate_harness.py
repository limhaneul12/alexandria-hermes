"""Deterministic harness for agent-authored skill candidates."""

from __future__ import annotations

from dataclasses import dataclass

from app.library.domain.event_enum.skill_enums import SkillCandidateHarnessStatus
from app.library.domain.types.skill_payload_types import (
    SkillCandidateHarnessCheckPayload,
    SkillCandidateHarnessPayload,
)


@dataclass(frozen=True, slots=True)
class SkillCandidateHarnessCheck:
    """One deterministic skill candidate check."""

    name: str
    passed: bool
    message: str

    def to_payload(self) -> SkillCandidateHarnessCheckPayload:
        """Convert this check to a persistent payload.

        Returns:
            SkillCandidateHarnessCheckPayload: JSON-compatible check payload.
        """
        payload = SkillCandidateHarnessCheckPayload(
            name=self.name,
            passed=self.passed,
            message=self.message,
        )
        return payload


@dataclass(frozen=True, slots=True)
class SkillCandidateHarnessResult:
    """Deterministic validation result for a skill candidate."""

    status: SkillCandidateHarnessStatus
    checks: tuple[SkillCandidateHarnessCheck, ...]

    def to_payload(self) -> SkillCandidateHarnessPayload:
        """Convert this harness result to a persistent payload.

        Returns:
            SkillCandidateHarnessPayload: JSON-compatible harness payload.
        """
        payload = SkillCandidateHarnessPayload(
            status=self.status.value,
            checks=[check.to_payload() for check in self.checks],
        )
        return payload


def run_skill_candidate_harness(
    title: str,
    purpose: str,
    content: str,
    evidence_urls: list[str],
) -> SkillCandidateHarnessResult:
    """Run deterministic checks for a self-acquired skill candidate.

    Args:
        title: Candidate title.
        purpose: Candidate purpose.
        content: Candidate Markdown content.
        evidence_urls: Source URLs gathered by the agent.

    Returns:
        SkillCandidateHarnessResult: Deterministic candidate validation result.
    """
    checks = (
        _presence_check(
            name="title_present",
            value=title,
            present_message="title is present",
            missing_message="title is required",
        ),
        _presence_check(
            name="purpose_present",
            value=purpose,
            present_message="purpose is present",
            missing_message="purpose is required",
        ),
        _presence_check(
            name="content_present",
            value=content,
            present_message="content is present",
            missing_message="content is required",
        ),
        _evidence_check(evidence_urls),
    )
    status = SkillCandidateHarnessStatus.PASSED
    if not all(check.passed for check in checks):
        status = SkillCandidateHarnessStatus.NEEDS_REVIEW
    result = SkillCandidateHarnessResult(status=status, checks=checks)
    return result


def _presence_check(
    name: str,
    value: str,
    present_message: str,
    missing_message: str,
) -> SkillCandidateHarnessCheck:
    passed = bool(value.strip())
    message = present_message if passed else missing_message
    check = SkillCandidateHarnessCheck(
        name=name,
        passed=passed,
        message=message,
    )
    return check


def _evidence_check(evidence_urls: list[str]) -> SkillCandidateHarnessCheck:
    normalized_urls = [url for url in evidence_urls if url.strip()]
    passed = bool(normalized_urls)
    message = (
        "evidence URL is present" if passed else "at least one evidence URL is required"
    )
    check = SkillCandidateHarnessCheck(
        name="evidence_present",
        passed=passed,
        message=message,
    )
    return check
