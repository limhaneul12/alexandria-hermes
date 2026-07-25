"""Canonical Markdown serializer for Obsidian-backed Memory Compacts."""

from __future__ import annotations

from datetime import datetime
from typing import cast

from app.memory.domain.entities.memory_compact import MemoryCompact
from app.memory.infrastructure.repositories.memory_compacts.obsidian_markdown_contracts import (
    ALEXANDRIA_MEMORY_COMPACT_TYPE,
    DEFAULT_MEMORY_COMPACT_SOURCE,
    DEFAULT_MEMORY_COMPACT_TAGS,
    FRONTMATTER_DELIMITER,
)
from app.shared.serialization.orjson_codec import dumps_json
from app.shared.types.extra_types import JSONValue
from app.shared.types.types_convert_utils import aware_utc_datetime


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
            "source_hash": source_ref.source_hash,
        }
        for source_ref in compact.source_refs
    ]
    frontmatter = {
        "alexandria_type": ALEXANDRIA_MEMORY_COMPACT_TYPE,
        "id": compact.id,
        "tags": DEFAULT_MEMORY_COMPACT_TAGS,
        "status": compact.status.value,
        "source": DEFAULT_MEMORY_COMPACT_SOURCE,
        "project": compact.project,
        "covered_from": _isoformat(compact.covered_from),
        "covered_to": _isoformat(compact.covered_to),
        "created_at": _isoformat(compact.created_at),
        "updated_at": _isoformat(compact.updated_at),
        "archived_at": _isoformat(compact.archived_at)
        if compact.archived_at is not None
        else None,
        "review_verdict": compact.review_verdict.value
        if compact.review_verdict is not None
        else None,
        "review_score": str(compact.review_score)
        if compact.review_score is not None
        else None,
        "review_max_score": str(compact.review_max_score)
        if compact.review_max_score is not None
        else None,
        "reviewed_at": _isoformat(compact.reviewed_at)
        if compact.reviewed_at is not None
        else None,
        "source_refs": dumps_json(cast(JSONValue, source_refs)).decode("utf-8"),
    }
    lines = [FRONTMATTER_DELIMITER]
    lines.extend(f"{key}: {_yaml_scalar(value)}" for key, value in frontmatter.items())
    lines.append(FRONTMATTER_DELIMITER)
    body = compact.markdown_body.rstrip("\n")
    return "\n".join(lines) + f"\n{body}\n"


def _isoformat(value: datetime) -> str:
    return aware_utc_datetime(value).isoformat().replace("+00:00", "Z")


def _yaml_scalar(value: str | None) -> str:
    if value is None:
        return "null"
    if value.startswith("[") and value.endswith("]"):
        return value
    escaped = value.replace("'", "''")
    return f"'{escaped}'"
