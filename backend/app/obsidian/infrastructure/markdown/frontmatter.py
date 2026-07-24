"""Markdown frontmatter parsing and rendering for Alexandria notes."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime

from app.shared.types.extra_types import JSONObject, JSONValue

FRONTMATTER_DELIMITER = "---"
type FrontmatterValue = str | list[str] | None


@dataclass(frozen=True, slots=True)
class MarkdownDocument:
    """A Markdown file split into frontmatter and body."""

    frontmatter: dict[str, FrontmatterValue]
    body: str


def parse_markdown_document(text: str) -> MarkdownDocument:
    """Parse a Markdown document with optional YAML frontmatter.

    Args:
        text: Markdown file content.

    Returns:
        Parsed frontmatter and body. Unsupported nested YAML is ignored rather
        than guessed because Alexandria only owns a small frontmatter subset.
    """
    lines = text.splitlines()
    if not lines or lines[0].strip() != FRONTMATTER_DELIMITER:
        return MarkdownDocument(frontmatter={}, body=text)
    end_index = _frontmatter_end_index(lines)
    if end_index is None:
        raise ValueError("FRONTMATTER_PARSE_ERROR: unterminated frontmatter")
    frontmatter = _parse_frontmatter_lines(lines[1:end_index])
    body = "\n".join(lines[end_index + 1 :])
    if text.endswith("\n") and body:
        body = f"{body}\n"
    return MarkdownDocument(frontmatter=frontmatter, body=body)


def render_markdown_document(frontmatter: JSONObject, body: str) -> str:
    """Render frontmatter and body into one Markdown document.

    Args:
        frontmatter: JSON-compatible frontmatter values.
        body: Markdown body content.

    Returns:
        Complete Markdown document.
    """
    lines = [FRONTMATTER_DELIMITER]
    for key, value in frontmatter.items():
        lines.extend(_render_frontmatter_value(key, value))
    lines.append(FRONTMATTER_DELIMITER)
    normalized_body = body.rstrip("\n")
    return "\n".join(lines) + f"\n\n{normalized_body}\n"


def update_frontmatter_scalars(
    text: str,
    replacements: Mapping[str, str],
) -> str:
    """Update top-level scalar fields without rewriting unknown YAML structure.

    Args:
        text: Complete Markdown document with frontmatter.
        replacements: Top-level scalar values to replace or append.

    Returns:
        Markdown with all unrelated frontmatter bytes and body lines preserved.

    Raises:
        ValueError: If the document has no complete frontmatter block.
    """
    lines = text.splitlines(keepends=True)
    if not lines or lines[0].rstrip("\r\n").strip() != FRONTMATTER_DELIMITER:
        raise ValueError("FRONTMATTER_PARSE_ERROR: frontmatter is required")
    end_index = next(
        (
            index
            for index, line in enumerate(lines[1:], start=1)
            if line.rstrip("\r\n").strip() == FRONTMATTER_DELIMITER
        ),
        None,
    )
    if end_index is None:
        raise ValueError("FRONTMATTER_PARSE_ERROR: unterminated frontmatter")
    matched_keys: set[str] = set()
    for index in range(1, end_index):
        raw_line = lines[index].rstrip("\r\n")
        if raw_line != raw_line.lstrip() or ":" not in raw_line:
            continue
        key = raw_line.split(":", maxsplit=1)[0].strip()
        value = replacements.get(key)
        if value is None:
            continue
        matched_keys.add(key)
        line_ending = lines[index][len(raw_line) :]
        lines[index] = f"{key}: {_yaml_scalar(value)}{line_ending}"
    remaining = {
        key: value for key, value in replacements.items() if key not in matched_keys
    }
    if remaining:
        default_ending = "\r\n" if lines[0].endswith("\r\n") else "\n"
        additions = [
            f"{key}: {_yaml_scalar(value)}{default_ending}"
            for key, value in remaining.items()
        ]
        lines[end_index:end_index] = additions
    return "".join(lines)


def frontmatter_json(frontmatter: dict[str, FrontmatterValue]) -> JSONObject:
    """Convert parsed frontmatter values into a JSON payload.

    Args:
        frontmatter: Parsed frontmatter map.

    Returns:
        JSON-compatible frontmatter payload.
    """
    payload: JSONObject = {}
    for key, value in frontmatter.items():
        payload[key] = _json_value(value)
    return payload


def frontmatter_text(frontmatter: dict[str, FrontmatterValue], key: str) -> str | None:
    """Read one scalar frontmatter value.

    Args:
        frontmatter: Parsed frontmatter map.
        key: Field to read.

    Returns:
        String value, or None for absent/non-scalar values.
    """
    value = frontmatter.get(key)
    if isinstance(value, str):
        return value
    return None


def frontmatter_list(frontmatter: dict[str, FrontmatterValue], key: str) -> list[str]:
    """Read one list frontmatter value.

    Args:
        frontmatter: Parsed frontmatter map.
        key: Field to read.

    Returns:
        List of string values.
    """
    value = frontmatter.get(key)
    if isinstance(value, list):
        return value
    if isinstance(value, str) and value:
        return [value]
    return []


def _frontmatter_end_index(lines: list[str]) -> int | None:
    for index, line in enumerate(lines[1:], start=1):
        if line.strip() == FRONTMATTER_DELIMITER:
            return index
    return None


def _parse_frontmatter_lines(lines: list[str]) -> dict[str, FrontmatterValue]:
    frontmatter: dict[str, FrontmatterValue] = {}
    active_list_key: str | None = None
    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if active_list_key is not None and stripped.startswith("-"):
            raw_item = stripped.removeprefix("-").strip()
            current = frontmatter.get(active_list_key)
            if isinstance(current, list):
                current.append(_parse_scalar(raw_item) or "")
            continue
        if line != line.lstrip():
            continue
        active_list_key = None
        if ":" not in line:
            continue
        key, raw_value = line.split(":", 1)
        key = key.strip()
        value = raw_value.strip()
        if not key:
            continue
        if key in frontmatter:
            raise ValueError(f"FRONTMATTER_PARSE_ERROR: duplicate top-level key: {key}")
        if value == "":
            frontmatter[key] = []
            active_list_key = key
        elif value.startswith("[") and value.endswith("]"):
            frontmatter[key] = _parse_inline_list(value)
        else:
            frontmatter[key] = _parse_scalar(value)
    return frontmatter


def _parse_inline_list(value: str) -> list[str]:
    inner = value[1:-1].strip()
    if not inner:
        return []
    return [
        item
        for raw in inner.split(",")
        if (item := (_parse_scalar(raw.strip()) or "").strip())
    ]


def _parse_scalar(value: str) -> str | None:
    if value in {"", "null", "Null", "NULL", "~"}:
        return None
    if len(value) >= 2 and value[0] == "'" and value[-1] == "'":
        return value[1:-1].replace("''", "'")
    if len(value) >= 2 and value[0] == '"' and value[-1] == '"':
        return value[1:-1]
    return value


def _render_frontmatter_value(key: str, value: JSONValue) -> list[str]:
    if isinstance(value, list):
        return [f"{key}:", *[f"  - {_yaml_scalar(str(item))}" for item in value]]
    return [f"{key}: {_yaml_scalar(_string_value(value))}"]


def _string_value(value: JSONValue) -> str | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int | float):
        return str(value)
    if isinstance(value, str):
        return value
    return str(value)


def _yaml_scalar(value: str | None) -> str:
    if value is None:
        return "null"
    if _can_render_plain(value):
        return value
    escaped = value.replace("'", "''")
    return f"'{escaped}'"


def _can_render_plain(value: str) -> bool:
    if not value:
        return False
    if value in {"true", "false", "null"}:
        return True
    blocked = {":", "#", "[", "]", "{", "}", "\n", "'", '"'}
    if any(character in value for character in blocked):
        return False
    return not value.startswith(("-", "@", "`", "!", "&", "*"))


def _json_value(value: FrontmatterValue) -> JSONValue:
    if value is None:
        return None
    if isinstance(value, list):
        return list(value)
    return value


def timestamp_text(value: datetime) -> str:
    """Render a timestamp as an ISO-8601 string.

    Args:
        value: Datetime to render.

    Returns:
        ISO formatted datetime.
    """
    return value.isoformat().replace("+00:00", "Z")
