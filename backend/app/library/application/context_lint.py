"""Context Harness linting and secret-aware redaction."""

from __future__ import annotations

import re
from dataclasses import dataclass

from app.library.domain.event_enum.context_enums import (
    ContextKind,
    ContextStorageStatus,
)
from app.library.domain.types.context_payload_types import ContextLintNormalizedPayload

HIGH_BLOCK_PATTERNS = (
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    re.compile(r"(?im)^\s*\.env\b.*"),
)
TOKEN_ASSIGNMENT_PATTERN = re.compile(
    r"(?i)\b(api[_-]?key|token|secret|password)\s*[:=]\s*([\"']?)[A-Za-z0-9_./+=\-]{12,}\2"
)
LONG_BASE64_PATTERN = re.compile(r"\b[A-Za-z0-9+/]{48,}={0,2}\b")
HEADING_PATTERN = re.compile(r"^##\s+(.+)$", re.MULTILINE)

REQUIRED_HEADINGS_BY_KIND: dict[ContextKind, tuple[str, ...]] = {
    ContextKind.HANDOFF: ("Summary", "Current State", "Next Actions", "Restore Prompt"),
    ContextKind.COMPACT: ("Summary", "Current State", "Next Actions", "Restore Prompt"),
    ContextKind.DECISION: ("Summary", "Key Decisions", "Evidence"),
    ContextKind.BUG_ROOT_CAUSE: ("Summary", "Current State", "Evidence"),
    ContextKind.PLAN: ("Summary", "Current State", "Next Actions"),
    ContextKind.RESEARCH: ("Summary", "Evidence"),
    ContextKind.USAGE: ("Summary", "Evidence"),
    ContextKind.MEMORY: ("Summary", "Restore Prompt"),
}


@dataclass(frozen=True, slots=True)
class ContextLintInput:
    """Input contract for linting context content."""

    kind: ContextKind
    title: str
    content: str
    summary: str | None
    project: str | None
    source_agent: str
    tags: list[str]


@dataclass(frozen=True, slots=True)
class ContextLintResult:
    """Machine-readable lint result."""

    ok: bool
    status: ContextStorageStatus
    score: int
    errors: list[str]
    warnings: list[str]
    suggestions: list[str]
    redacted_content: str
    normalized: ContextLintNormalizedPayload


def lint_context(payload: ContextLintInput) -> ContextLintResult:
    """Validate and redact a context before persistence.

    Args:
        payload: Context lint input.

    Returns:
        Lint result with redacted content and quality metadata.
    """
    errors: list[str] = []
    warnings: list[str] = []
    suggestions: list[str] = []

    title = payload.title.strip()
    content = payload.content.strip()
    summary = (payload.summary or "").strip()
    if not title:
        errors.append("title is required")
    if not content:
        errors.append("content is required")
    if not summary:
        warnings.append("summary is recommended")
        suggestions.append("Add a 1-3 sentence summary for better recall.")

    headings = {match.group(1).strip() for match in HEADING_PATTERN.finditer(content)}
    warnings.extend(
        f"missing heading: {required}"
        for required in REQUIRED_HEADINGS_BY_KIND[payload.kind]
        if required not in headings
    )

    blocked = any(pattern.search(content) for pattern in HIGH_BLOCK_PATTERNS)
    redacted = content
    redaction_count = 0
    if not blocked:
        redacted, token_redactions = TOKEN_ASSIGNMENT_PATTERN.subn(
            lambda match: f"{match.group(1)}=<REDACTED>", redacted
        )
        redaction_count += token_redactions
        redacted, base64_redactions = LONG_BASE64_PATTERN.subn(
            "<REDACTED_LONG_VALUE>", redacted
        )
        redaction_count += base64_redactions

    if blocked:
        errors.append("high-risk secret content cannot be saved raw")
        status = ContextStorageStatus.BLOCKED_SECRET_RISK
    elif redaction_count > 0:
        warnings.append("potential secret-like content was redacted")
        status = ContextStorageStatus.REDACTED_AND_SAVED
    elif warnings:
        status = ContextStorageStatus.SAVED_WITH_WARNINGS
    else:
        status = ContextStorageStatus.SAVED

    score = max(0, 100 - len(errors) * 40 - len(warnings) * 8)
    if score < 70 and status is not ContextStorageStatus.BLOCKED_SECRET_RISK:
        status = ContextStorageStatus.PENDING_REVIEW
        warnings.append("quality score below review threshold")

    normalized: ContextLintNormalizedPayload = {
        "kind": payload.kind,
        "title": title,
        "summary": summary,
        "project": payload.project,
        "source_agent": payload.source_agent.strip(),
        "tags": sorted({tag.strip() for tag in payload.tags if tag.strip()}),
    }
    result = ContextLintResult(
        ok=not errors,
        status=status,
        score=score,
        errors=errors,
        warnings=warnings,
        suggestions=suggestions,
        redacted_content=redacted,
        normalized=normalized,
    )
    return result
