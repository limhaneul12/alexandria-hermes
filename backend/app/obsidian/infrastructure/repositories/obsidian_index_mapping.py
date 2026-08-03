"""Mapping helpers for Obsidian index ORM rows."""

from __future__ import annotations

from collections.abc import Sequence
from typing import cast

from app.obsidian.domain.entities.obsidian_note import (
    ObsidianEdge,
    ObsidianNote,
)
from app.obsidian.domain.event_enum.obsidian_enums import (
    AlexandriaNoteType,
    ObsidianEdgeSourceKind,
    ObsidianIndexStatus,
    ObsidianRelationType,
)
from app.obsidian.infrastructure.models.obsidian_index_models import (
    ObsidianEdgeORM,
    ObsidianFileORM,
)
from app.shared.types.extra_types import JSONObject


def note_from_model(model: ObsidianFileORM) -> ObsidianNote:
    return ObsidianNote(
        note_id=model.note_id,
        relative_path=model.relative_path,
        alexandria_type=AlexandriaNoteType(model.alexandria_type),
        title=model.title,
        status=model.status,
        tags=tuple(model.tags),
        project=model.project,
        source=model.source,
        content_hash=model.content_hash,
        frontmatter=cast(JSONObject, model.frontmatter_json),
        body=model.body,
        index_status=ObsidianIndexStatus(model.index_status),
        error_message=model.error_message,
        size_bytes=model.size_bytes,
        modified_at=model.modified_at,
        indexed_at=model.indexed_at,
    )


def edge_from_model(model: ObsidianEdgeORM) -> ObsidianEdge:
    return ObsidianEdge(
        edge_id=model.edge_id,
        source_note_id=model.source_note_id,
        source_path=model.source_path,
        target_note_id=model.target_note_id,
        target_path=model.target_path,
        relation=ObsidianRelationType(model.relation),
        confidence=model.confidence,
        source_kind=ObsidianEdgeSourceKind(model.source_kind),
        created_at=model.created_at,
        indexed_at=model.indexed_at,
    )


def matches_tags(tags: Sequence[str], required: Sequence[str]) -> bool:
    if not required:
        return True
    tag_set = set(tags)
    return all(tag in tag_set for tag in required)


def obsidian_excerpt(text: str, limit: int = 240) -> str:
    normalized = " ".join(text.split())
    if len(normalized) <= limit:
        return normalized
    return f"{normalized[: limit - 1]}…"
