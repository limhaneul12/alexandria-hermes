"""Skill candidate harness behavior tests."""

from __future__ import annotations

from app.library.application.quality_gate import run_library_quality_gate
from app.library.application.skills.candidate_harness import (
    run_skill_candidate_harness,
)
from app.library.domain.event_enum.item_enums import ItemType


def test_skill_candidate_harness_passes_when_candidate_has_evidence() -> None:
    """Self-acquired candidates should pass when content and evidence exist."""
    result = run_skill_candidate_harness(
        title="FastAPI skill",
        purpose="Teach route testing",
        content="# FastAPI\nUse dependency overrides.",
        evidence_urls=["https://example.com/fastapi"],
    )

    assert result.to_payload() == {
        "status": "PASSED",
        "checks": [
            {"name": "title_present", "passed": True, "message": "title is present"},
            {
                "name": "purpose_present",
                "passed": True,
                "message": "purpose is present",
            },
            {
                "name": "content_present",
                "passed": True,
                "message": "content is present",
            },
            {
                "name": "evidence_present",
                "passed": True,
                "message": "evidence URL is present",
            },
        ],
    }


def test_skill_candidate_harness_needs_review_when_evidence_is_missing() -> None:
    """Self-acquired candidates should be review-gated without source evidence."""
    result = run_skill_candidate_harness(
        title="FastAPI skill",
        purpose="Teach route testing",
        content="# FastAPI\nUse dependency overrides.",
        evidence_urls=[],
    )

    assert result.to_payload()["status"] == "NEEDS_REVIEW"


def test_library_quality_gate_redacts_secrets_and_marks_review_needed() -> None:
    """Library quality gate should avoid storing raw secret-bearing content."""
    result = run_library_quality_gate(
        item_type=ItemType.PROMPT,
        title="Token prompt",
        content="Use API_TOKEN=sk-live-secret-value-12345678901234567890",
    )

    payload = result.to_payload()
    assert result.redacted_content != (
        "Use API_TOKEN=sk-live-secret-value-12345678901234567890"
    )
    assert payload["status"] == "PASSED"
    assert {
        "name": "secret_redaction",
        "passed": True,
        "message": "secret content is redacted or safe",
    } in payload["checks"]


def test_library_quality_gate_blocks_dangerous_command_markers() -> None:
    """Library quality gate should flag destructive command recipes for review."""
    result = run_library_quality_gate(
        item_type=ItemType.SKILL,
        title="Dangerous cleanup",
        content="Run rm -rf / to clean everything.",
        evidence_urls=["https://example.com/review"],
    )

    payload = result.to_payload()
    assert payload["status"] == "NEEDS_REVIEW"
    assert {
        "name": "dangerous_command_absent",
        "passed": False,
        "message": "dangerous shell command marker is absent",
    } in payload["checks"]
