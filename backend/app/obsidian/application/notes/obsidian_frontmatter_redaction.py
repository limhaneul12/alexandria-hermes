"""Secret redaction helpers for Obsidian frontmatter payloads."""

from __future__ import annotations

from app.shared.exceptions import ObsidianValidationError
from app.shared.types.extra_types import JSONObject, JSONValue
from app.shared.utils.secret_redaction import redact_secret_text


def redacted_frontmatter(frontmatter: JSONObject) -> tuple[JSONObject, list[str]]:
    """Return frontmatter with string values redacted before persistence.

    Args:
        frontmatter: Caller-provided frontmatter object.

    Returns:
        Redacted frontmatter and user-facing warnings.
    """
    redacted, warnings = _redacted_json(frontmatter)
    return dict(redacted) if isinstance(redacted, dict) else {}, warnings


def _redacted_json(value: JSONValue) -> tuple[JSONValue, list[str]]:
    if isinstance(value, str):
        redaction = redact_secret_text(value)
        if redaction.blocked:
            raise ObsidianValidationError(
                "high-risk secret content cannot be saved in frontmatter"
            )
        return redaction.redacted_content, redaction.warnings
    if isinstance(value, list | tuple):
        return _redacted_sequence(value)
    if isinstance(value, dict):
        return _redacted_mapping(value)
    return value, []


def _redacted_sequence(
    value: list[JSONValue] | tuple[JSONValue, ...],
) -> tuple[
    list[JSONValue],
    list[str],
]:
    items: list[JSONValue] = []
    warnings: list[str] = []
    for item in value:
        redacted_item, item_warnings = _redacted_json(item)
        items.append(redacted_item)
        warnings.extend(item_warnings)
    return items, _dedupe_warnings(warnings)


def _redacted_mapping(value: dict[str, JSONValue]) -> tuple[JSONObject, list[str]]:
    payload: JSONObject = {}
    warnings: list[str] = []
    for key, item in value.items():
        redacted_item, item_warnings = _redacted_json(item)
        payload[str(key)] = redacted_item
        warnings.extend(item_warnings)
    return payload, _dedupe_warnings(warnings)


def _dedupe_warnings(warnings: list[str]) -> list[str]:
    deduped: list[str] = []
    for warning in warnings:
        if warning not in deduped:
            deduped.append(warning)
    return deduped
