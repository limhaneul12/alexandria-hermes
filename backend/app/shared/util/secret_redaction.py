"""Shared secret detection and redaction helpers for persistence boundaries."""

from __future__ import annotations

import re
from dataclasses import dataclass

HIGH_RISK_SECRET_PATTERNS = (
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    re.compile(r"(?im)^\s*\.env\b.*"),
)
TOKEN_ASSIGNMENT_PATTERN = re.compile(
    r"(?i)\b(api[_-]?key|token|secret|password)\s*[:=]\s*([\"']?)[A-Za-z0-9_./+=\-]{12,}\2"
)
LONG_TOKEN_PATTERN = re.compile(r"\b[A-Za-z0-9+/._=-]{48,}\b")


@dataclass(frozen=True, slots=True)
class SecretRedactionResult:
    """Result returned after secret scanning text content."""

    blocked: bool
    redacted_content: str
    redaction_count: int
    warnings: list[str]


def redact_secret_text(content: str) -> SecretRedactionResult:
    """Detect and redact token-like content before long-term storage.

    Args:
        content: Raw text headed toward a persistent boundary.

    Returns:
        SecretRedactionResult: Redaction result and user-facing warnings.
    """
    blocked = any(pattern.search(content) for pattern in HIGH_RISK_SECRET_PATTERNS)
    if blocked:
        return SecretRedactionResult(
            blocked=True,
            redacted_content=content,
            redaction_count=0,
            warnings=["high-risk secret content cannot be saved raw"],
        )

    redacted, assignment_count = TOKEN_ASSIGNMENT_PATTERN.subn(
        lambda match: f"{match.group(1)}=<REDACTED>", content
    )
    redacted, token_count = LONG_TOKEN_PATTERN.subn("<REDACTED_LONG_VALUE>", redacted)
    redaction_count = assignment_count + token_count
    warnings: list[str] = []
    if redaction_count > 0:
        warnings.append("potential secret-like content was redacted")
    return SecretRedactionResult(
        blocked=False,
        redacted_content=redacted,
        redaction_count=redaction_count,
        warnings=warnings,
    )
