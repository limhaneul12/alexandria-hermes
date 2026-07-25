"""Frontmatter parser for Obsidian-backed Memory Compact notes."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import cast

from app.memory.domain.entities.memory_compact import (
    MemoryCompact,
    MemoryCompactSourceRef,
)
from app.memory.domain.event_enum.memory_compact_enums import (
    MemoryCompactReviewVerdict,
    MemoryCompactStatus,
)
from app.memory.infrastructure.repositories.memory_compacts.obsidian_markdown_contracts import (
    ALEXANDRIA_MEMORY_COMPACT_TYPE,
    FRONTMATTER_DELIMITER,
    UPDATED_AT_KEYS,
)
from app.shared.infrastructure.identifiers import new_uuid
from app.shared.serialization.orjson_codec import loads_json
from app.shared.types.extra_types import JSONObject, JSONValue
from app.shared.types.types_convert_utils import aware_utc_datetime


def read_compact_file(path: Path) -> MemoryCompact | None:
    """Read one Obsidian note when it is an Alexandria Memory Compact.

    Args:
        path: Markdown note path.

    Returns:
        Memory Compact entity when the note has the expected frontmatter.
    """
    try:
        frontmatter, body = _read_frontmatter(path.read_text(encoding="utf-8"))
    except OSError:
        return None
    if frontmatter.get("alexandria_type") != ALEXANDRIA_MEMORY_COMPACT_TYPE:
        return None
    return _compact_from_frontmatter(frontmatter, body)


def _read_frontmatter(text: str) -> tuple[dict[str, str | None], str]:
    lines = text.splitlines()
    if not lines or lines[0].strip() != FRONTMATTER_DELIMITER:
        return {}, text
    try:
        end_index = next(
            index
            for index, line in enumerate(lines[1:], start=1)
            if line.strip() == FRONTMATTER_DELIMITER
        )
    except StopIteration:
        return {}, text
    frontmatter: dict[str, str | None] = {}
    for line in lines[1:end_index]:
        if not line.strip() or line.lstrip().startswith("#") or ":" not in line:
            continue
        key, raw_value = line.split(":", 1)
        frontmatter[key.strip()] = _parse_yaml_scalar(raw_value.strip())
    body = "\n".join(lines[end_index + 1 :])
    return frontmatter, body


def _compact_from_frontmatter(
    frontmatter: dict[str, str | None], body: str
) -> MemoryCompact | None:
    try:
        compact_id = _required_text(frontmatter, "id")
        status = _status_from_frontmatter(frontmatter)
        created_at = _datetime_from_frontmatter(
            frontmatter, ("created_at", "created", "date")
        )
        updated_at_missing = not any(frontmatter.get(key) for key in UPDATED_AT_KEYS)
        updated_at = _datetime_from_frontmatter(
            frontmatter, UPDATED_AT_KEYS, fallback=created_at
        )
        covered_from = _datetime_from_frontmatter(
            frontmatter, ("covered_from",), fallback=created_at
        )
        covered_to = _datetime_from_frontmatter(
            frontmatter, ("covered_to",), fallback=updated_at
        )
        return MemoryCompact(
            id=compact_id,
            project=frontmatter.get("project"),
            covered_from=covered_from,
            covered_to=covered_to,
            markdown_body=body.rstrip("\n"),
            status=status,
            source_refs=_source_refs_from_json(
                frontmatter.get("source_refs"), compact_id=compact_id
            ),
            created_at=created_at,
            updated_at=updated_at,
            archived_at=_optional_datetime(frontmatter.get("archived_at")),
            review_verdict=_optional_review_verdict(frontmatter.get("review_verdict")),
            review_score=_optional_int(frontmatter.get("review_score")),
            review_max_score=_optional_int(frontmatter.get("review_max_score")),
            reviewed_at=_optional_datetime(frontmatter.get("reviewed_at")),
            metadata_warnings=(
                ("memory_compact_timestamp_missing",) if updated_at_missing else ()
            ),
        )
    except (KeyError, TypeError, ValueError):
        return None


def _source_refs_from_json(
    value: str | None, *, compact_id: str
) -> tuple[MemoryCompactSourceRef, ...]:
    if not value:
        return ()
    try:
        decoded = loads_json(value)
    except ValueError:
        return ()
    if not isinstance(decoded, list):
        return ()
    refs: list[MemoryCompactSourceRef] = []
    for item in decoded:
        if not isinstance(item, dict):
            continue
        payload = cast(JSONObject, item)
        refs.append(
            MemoryCompactSourceRef(
                id=str(payload.get("id") or new_uuid()),
                compact_id=str(payload.get("compact_id") or compact_id),
                source_type=str(payload.get("source_type") or ""),
                source_id=str(payload.get("source_id") or ""),
                title=str(payload.get("title") or ""),
                detail_path=str(payload.get("detail_path") or ""),
                source_hash=_optional_string(payload.get("source_hash")),
            )
        )
    return tuple(refs)


def _required_text(frontmatter: dict[str, str | None], key: str) -> str:
    value = frontmatter[key]
    if value is None or not value:
        raise ValueError(f"Missing Memory Compact frontmatter: {key}")
    return value


def _optional_string(value: JSONValue | None) -> str | None:
    if isinstance(value, str) and value.strip():
        return value.strip()
    return None


def _status_from_frontmatter(
    frontmatter: dict[str, str | None],
) -> MemoryCompactStatus:
    value = _required_text(frontmatter, "status")
    return MemoryCompactStatus(value.strip().upper())


def _datetime_from_frontmatter(
    frontmatter: dict[str, str | None],
    keys: tuple[str, ...],
    *,
    fallback: datetime | None = None,
) -> datetime:
    for key in keys:
        value = frontmatter.get(key)
        if value:
            return _parse_datetime(value)
    if fallback is not None:
        return fallback
    joined_keys = ", ".join(keys)
    raise ValueError(f"Missing Memory Compact frontmatter: {joined_keys}")


def _optional_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    return _parse_datetime(value)


def _optional_review_verdict(value: str | None) -> MemoryCompactReviewVerdict | None:
    if not value:
        return None
    return MemoryCompactReviewVerdict(value)


def _optional_int(value: str | None) -> int | None:
    if not value:
        return None
    return int(value)


def _parse_datetime(value: str) -> datetime:
    return aware_utc_datetime(datetime.fromisoformat(value.replace("Z", "+00:00")))


def _parse_yaml_scalar(value: str) -> str | None:
    if value in {"", "null", "Null", "NULL", "~"}:
        return None
    if len(value) >= 2 and value[0] == "'" and value[-1] == "'":
        return value[1:-1].replace("''", "'")
    if len(value) >= 2 and value[0] == '"' and value[-1] == '"':
        return value[1:-1]
    return value
