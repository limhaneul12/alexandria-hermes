"""Deterministic quality gates for shared skill and prompt library assets."""

from __future__ import annotations

from dataclasses import dataclass

from app.library.domain.event_enum.item_enums import ItemType
from app.shared.types.extra_types import JSONObject
from app.shared.utils.secret_redaction import redact_secret_text

DANGEROUS_COMMAND_MARKERS = ("rm -rf /", "docker volume rm", "kubectl delete")


@dataclass(frozen=True, slots=True)
class LibraryQualityGateResult:
    """Quality gate decision for one skill or prompt asset."""

    status: str
    checks: list[JSONObject]
    redacted_content: str

    def to_payload(self) -> JSONObject:
        """Return a JSON-compatible payload for item details.

        Returns:
            JSONObject: Persistent quality gate metadata.
        """
        payload: JSONObject = {
            "status": self.status,
            "checks": self.checks,
        }
        return payload


def run_library_quality_gate(
    item_type: ItemType,
    title: str,
    content: str,
    evidence_urls: list[str] | None = None,
    source_summary: str | None = None,
) -> LibraryQualityGateResult:
    """Run deterministic quality and safety checks for a library asset.

    Args:
        item_type: Library item kind being evaluated.
        title: Item title.
        content: Item body.
        evidence_urls: Optional source URLs for generated candidates.
        source_summary: Optional source summary for generated candidates.

    Returns:
        LibraryQualityGateResult: Gate metadata and redacted content.
    """
    redaction = redact_secret_text(content)
    checks = [
        _check("title_present", bool(title.strip()), "title is present"),
        _check("content_present", bool(content.strip()), "content is present"),
        _check(
            "dangerous_command_absent",
            not _contains_dangerous_command(content),
            "dangerous shell command marker is absent",
        ),
        _check(
            "secret_redaction",
            not redaction.blocked,
            "secret content is redacted or safe",
        ),
    ]
    if item_type is ItemType.SKILL:
        checks.append(
            _check(
                "evidence_or_summary_present",
                bool(evidence_urls) or bool((source_summary or "").strip()),
                "evidence URL or source summary is present",
            )
        )
    status = (
        "PASSED" if all(bool(check["passed"]) for check in checks) else "NEEDS_REVIEW"
    )
    return LibraryQualityGateResult(
        status=status,
        checks=checks,
        redacted_content=redaction.redacted_content,
    )


def _check(name: str, passed: bool, message: str) -> JSONObject:
    return {"name": name, "passed": passed, "message": message}


def _contains_dangerous_command(content: str) -> bool:
    lowered = content.lower()
    return any(marker in lowered for marker in DANGEROUS_COMMAND_MARKERS)
