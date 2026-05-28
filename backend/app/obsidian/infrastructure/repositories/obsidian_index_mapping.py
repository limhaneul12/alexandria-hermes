"""Mapping helpers for Obsidian index ORM rows."""

from __future__ import annotations

from typing import cast

from app.obsidian.domain.entities.obsidian_note import (
    ObsidianEdge,
    ObsidianNote,
    ObsidianRelatedNote,
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
        tags=list(model.tags),
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


def add_related_result(
    results: dict[str, ObsidianRelatedNote],
    edge: ObsidianEdgeORM,
    note_model: ObsidianFileORM,
    *,
    direction: str,
) -> None:
    note = note_from_model(note_model)
    if note.note_id == edge.source_note_id and direction == "outgoing":
        return
    edge_entity = edge_from_model(edge)
    score = _relation_weight(edge_entity.relation) + edge_entity.confidence
    result = ObsidianRelatedNote(
        note=note,
        relation=edge_entity.relation,
        source_kind=edge_entity.source_kind,
        direction=direction,
        score=score,
        edge_id=edge_entity.edge_id,
    )
    current = results.get(note.note_id)
    if current is None or result.score > current.score:
        results[note.note_id] = result


def _relation_weight(relation: ObsidianRelationType) -> float:
    return {
        ObsidianRelationType.DERIVED_FROM: 1.0,
        ObsidianRelationType.CITES: 0.9,
        ObsidianRelationType.SUPERSEDES: 0.8,
        ObsidianRelationType.PROMOTES_TO: 0.8,
        ObsidianRelationType.RELATED: 0.6,
        ObsidianRelationType.WIKILINK: 0.5,
        ObsidianRelationType.BLOCKS: 0.4,
        ObsidianRelationType.RESOLVES: 0.4,
    }[relation]


def matches_tags(tags: list[str], required: list[str]) -> bool:
    if not required:
        return True
    tag_set = set(tags)
    return all(tag in tag_set for tag in required)


def obsidian_excerpt(text: str, limit: int = 240) -> str:
    normalized = " ".join(text.split())
    if len(normalized) <= limit:
        return normalized
    return f"{normalized[: limit - 1]}…"
