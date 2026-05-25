"""Markdown serialization for Obsidian-backed Memory Compacts."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import cast

from app.memory.domain.entities.memory_compact import (
    MemoryCompact,
    MemoryCompactSourceRef,
)
from app.memory.domain.event_enum.memory_compact_enums import MemoryCompactStatus
from app.shared.infrastructure.identifiers import new_uuid
from app.shared.serialization.orjson_codec import dumps_json, loads_json
from app.shared.types.extra_types import JSONObject, JSONValue
from app.shared.types.types_convert_utils import aware_utc_datetime

FRONTMATTER_DELIMITER = "---"
NOTE_SUFFIX = ".md"
_ALEXANDRIA_TYPE = "memory_compact"
_DEFAULT_TAGS = "[alexandria, memory-compact]"
_DEFAULT_SOURCE = "alexandria-hermes"


def is_safe_note_id(compact_id: str) -> bool:
    """Return whether a compact id is safe for direct filename lookup.

    Args:
        compact_id: Memory Compact identifier.

    Returns:
        True when the identifier can be used as a local note filename.
    """
    if compact_id in {"", ".", ".."}:
        return False
    return (
        "/" not in compact_id
        and "\\" not in compact_id
        and ".." not in Path(compact_id).parts
    )


def resolve_base_dir(vault_path: str | Path, relative_dir: str | Path) -> Path:
    """Resolve the Memory Compact note directory inside an Obsidian vault.

    Args:
        vault_path: Obsidian vault root path.
        relative_dir: Memory Compact folder path relative to the vault.

    Returns:
        Absolute Memory Compact note directory path.
    """
    vault = Path(vault_path).expanduser()
    if not vault.is_absolute():
        vault = Path.cwd() / vault
    relative = Path(relative_dir)
    if relative.is_absolute() or ".." in relative.parts:
        raise ValueError("Memory Compact Obsidian directory must stay inside vault")
    return vault / relative


def serialize_compact(compact: MemoryCompact) -> str:
    """Serialize one Memory Compact entity into an Obsidian Markdown note.

    Args:
        compact: Memory Compact entity to write.

    Returns:
        Markdown note text with YAML frontmatter.
    """
    source_refs = [
        {
            "id": source_ref.id,
            "compact_id": source_ref.compact_id,
            "source_type": source_ref.source_type,
            "source_id": source_ref.source_id,
            "title": source_ref.title,
            "detail_path": source_ref.detail_path,
        }
        for source_ref in compact.source_refs
    ]
    frontmatter = {
        "alexandria_type": _ALEXANDRIA_TYPE,
        "id": compact.id,
        "tags": _DEFAULT_TAGS,
        "status": compact.status.value,
        "source": _DEFAULT_SOURCE,
        "project": compact.project,
        "covered_from": _isoformat(compact.covered_from),
        "covered_to": _isoformat(compact.covered_to),
        "created_at": _isoformat(compact.created_at),
        "updated_at": _isoformat(compact.updated_at),
        "archived_at": _isoformat(compact.archived_at)
        if compact.archived_at is not None
        else None,
        "source_refs": dumps_json(cast(JSONValue, source_refs)).decode("utf-8"),
    }
    lines = [FRONTMATTER_DELIMITER]
    lines.extend(f"{key}: {_yaml_scalar(value)}" for key, value in frontmatter.items())
    lines.append(FRONTMATTER_DELIMITER)
    body = compact.markdown_body.rstrip("\n")
    return "\n".join(lines) + f"\n{body}\n"


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
    if frontmatter.get("alexandria_type") != _ALEXANDRIA_TYPE:
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
        status = MemoryCompactStatus(_required_text(frontmatter, "status"))
        return MemoryCompact(
            id=compact_id,
            project=frontmatter.get("project"),
            covered_from=_required_datetime(frontmatter, "covered_from"),
            covered_to=_required_datetime(frontmatter, "covered_to"),
            markdown_body=body.rstrip("\n"),
            status=status,
            source_refs=_source_refs_from_json(
                frontmatter.get("source_refs"), compact_id=compact_id
            ),
            created_at=_required_datetime(frontmatter, "created_at"),
            updated_at=_required_datetime(frontmatter, "updated_at"),
            archived_at=_optional_datetime(frontmatter.get("archived_at")),
        )
    except (KeyError, TypeError, ValueError):
        return None


def _source_refs_from_json(
    value: str | None, *, compact_id: str
) -> tuple[MemoryCompactSourceRef, ...]:
    if not value:
        return ()
    decoded = loads_json(value)
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
            )
        )
    return tuple(refs)


def _required_text(frontmatter: dict[str, str | None], key: str) -> str:
    value = frontmatter[key]
    if value is None or not value:
        raise ValueError(f"Missing Memory Compact frontmatter: {key}")
    return value


def _required_datetime(frontmatter: dict[str, str | None], key: str) -> datetime:
    return _parse_datetime(_required_text(frontmatter, key))


def _optional_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    return _parse_datetime(value)


def _parse_datetime(value: str) -> datetime:
    return aware_utc_datetime(datetime.fromisoformat(value.replace("Z", "+00:00")))


def _isoformat(value: datetime) -> str:
    return aware_utc_datetime(value).isoformat().replace("+00:00", "Z")


def _yaml_scalar(value: str | None) -> str:
    if value is None:
        return "null"
    if value.startswith("[") and value.endswith("]"):
        return value
    escaped = value.replace("'", "''")
    return f"'{escaped}'"


def _parse_yaml_scalar(value: str) -> str | None:
    if value in {"", "null", "Null", "NULL", "~"}:
        return None
    if len(value) >= 2 and value[0] == "'" and value[-1] == "'":
        return value[1:-1].replace("''", "'")
    if len(value) >= 2 and value[0] == '"' and value[-1] == '"':
        return value[1:-1]
    return value
