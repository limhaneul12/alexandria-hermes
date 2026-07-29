"""Shared secret detection and redaction helpers for persistence boundaries."""

from __future__ import annotations

import re
from dataclasses import dataclass
from urllib.parse import unquote_plus

HIGH_RISK_SECRET_PATTERNS = (
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    re.compile(r"(?im)^\s*\.env\b.*"),
)
BLOCKED_SECRET_PLACEHOLDER = "[BLOCKED_SECRET_CONTENT]"
TOKEN_ASSIGNMENT_PATTERN = re.compile(
    r"(?i)\b(api[_-]?key|token|secret|password)\s*[:=]\s*([\"']?)[A-Za-z0-9_./+=\-]{12,}\2"
)
AUTHORIZATION_HEADER_PATTERN = re.compile(r"(?im)^(\s*authorization\s*:\s*)([^\r\n]+)")
BEARER_TOKEN_PATTERN = re.compile(r"(?i)\bbearer(\s+)[A-Za-z0-9._~+/=-]{4,}")
LONG_TOKEN_PATTERN = re.compile(r"\b[A-Za-z0-9+/._=-]{48,}\b")
URL_PATTERN = re.compile(r"https?://[^\s<>\"']+", re.IGNORECASE)
CREDENTIAL_QUERY_PARAMETER_NAMES = frozenset(
    {
        "token",
        "access_token",
        "refresh_token",
        "api_key",
        "apikey",
        "secret",
        "client_secret",
        "signature",
        "sig",
        "authorization",
        "auth",
        "password",
        "passwd",
        "session",
        "session_token",
    }
)
SECRET_FIELD_NAME_PATTERN = re.compile(
    r"(?i)(api[_-]?key|token|secret|password|credential|private[_-]?key)"
)


@dataclass(frozen=True, slots=True)
class SecretRedactionResult:
    """Result returned after secret scanning text content."""

    blocked: bool
    redacted_content: str
    redaction_count: int
    warnings: tuple[str, ...]


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
            redacted_content=BLOCKED_SECRET_PLACEHOLDER,
            redaction_count=1,
            warnings=("high-risk secret content cannot be saved raw",),
        )

    redacted, redaction_count = _redact_text_preserving_urls(content)
    warnings: list[str] = []
    if redaction_count > 0:
        warnings.append("potential secret-like content was redacted")
    return SecretRedactionResult(
        blocked=False,
        redacted_content=redacted,
        redaction_count=redaction_count,
        warnings=tuple(warnings),
    )


def _redact_text_preserving_urls(content: str) -> tuple[str, int]:
    redacted_parts: list[str] = []
    redaction_count = 0
    previous_end = 0
    for match in URL_PATTERN.finditer(content):
        text_part, text_count = _redact_non_url_text(
            content[previous_end : match.start()]
        )
        url, trailing_text = _split_url_trailing_text(match.group(0))
        url_part, url_count = _redact_url_query_credentials(url)
        redacted_parts.extend((text_part, url_part, trailing_text))
        redaction_count += text_count + url_count
        previous_end = match.end()

    text_part, text_count = _redact_non_url_text(content[previous_end:])
    redacted_parts.append(text_part)
    return "".join(redacted_parts), redaction_count + text_count


def _redact_non_url_text(content: str) -> tuple[str, int]:
    redacted, authorization_count = AUTHORIZATION_HEADER_PATTERN.subn(
        _redacted_authorization_header,
        content,
    )
    redacted, bearer_count = BEARER_TOKEN_PATTERN.subn(
        lambda match: f"Bearer{match.group(1)}<REDACTED>",
        redacted,
    )
    redacted, assignment_count = TOKEN_ASSIGNMENT_PATTERN.subn(
        lambda match: f"{match.group(1)}=<REDACTED>", redacted
    )
    redacted, token_count = LONG_TOKEN_PATTERN.subn("<REDACTED_LONG_VALUE>", redacted)
    return (
        redacted,
        authorization_count + bearer_count + assignment_count + token_count,
    )


def _redacted_authorization_header(match: re.Match[str]) -> str:
    value = match.group(2).strip()
    scheme, separator, _credential = value.partition(" ")
    if separator and scheme.casefold() in {"basic", "bearer", "digest"}:
        return f"{match.group(1)}{scheme} <REDACTED>"
    return f"{match.group(1)}<REDACTED>"


def _split_url_trailing_text(url: str) -> tuple[str, str]:
    trailing_start = len(url)
    while trailing_start > 0:
        character = url[trailing_start - 1]
        if character in ".,;:!?":
            trailing_start -= 1
            continue
        opening_character = {")": "(", "]": "[", "}": "{"}.get(character)
        if opening_character is None:
            break
        candidate = url[:trailing_start]
        if candidate.count(character) <= candidate.count(opening_character):
            break
        trailing_start -= 1
    return url[:trailing_start], url[trailing_start:]


def _redact_url_query_credentials(url: str) -> tuple[str, int]:
    url_without_fragment, fragment_separator, fragment = url.partition("#")
    url_path, query_separator, query = url_without_fragment.partition("?")
    redacted_query, query_redaction_count = _redact_url_parameter_values(query)
    redacted_fragment, fragment_redaction_count = _redact_url_parameter_values(fragment)

    redacted_url = url_path
    if query_separator:
        redacted_url = f"{redacted_url}?{redacted_query}"
    if fragment_separator:
        redacted_url = f"{redacted_url}#{redacted_fragment}"
    return redacted_url, query_redaction_count + fragment_redaction_count


def _redact_url_parameter_values(parameters: str) -> tuple[str, int]:
    parameter_parts = parameters.split("&")
    redaction_count = 0
    for index, parameter_part in enumerate(parameter_parts):
        name, value_separator, value = parameter_part.partition("=")
        normalized_name = unquote_plus(name).lower()
        if (
            value_separator
            and value
            and normalized_name in CREDENTIAL_QUERY_PARAMETER_NAMES
        ):
            parameter_parts[index] = f"{name}=<REDACTED>"
            redaction_count += 1
    return "&".join(parameter_parts), redaction_count


def is_secret_field_name(field_name: str) -> bool:
    """Return whether a structured field name denotes credential material.

    Args:
        field_name: Structured mapping key.

    Returns:
        True when the key denotes credential material.
    """
    return SECRET_FIELD_NAME_PATTERN.search(field_name) is not None
