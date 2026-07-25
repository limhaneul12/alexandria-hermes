"""Dynamic frontmatter target parsing for Obsidian graph relations."""

from __future__ import annotations

import ast
from collections.abc import Iterable, Mapping, Sequence
from typing import cast

from app.obsidian.domain.event_enum.obsidian_enums import ObsidianRelationType
from app.shared.types.extra_types import JSONObject, JSONValue


class _RelationTarget:
    def __init__(
        self,
        *,
        path: str | None,
        note_id: str | None,
        relation: ObsidianRelationType | None,
    ) -> None:
        self.path = path
        self.note_id = note_id
        self.relation = relation


def _relation_targets(value: JSONValue | None) -> Iterable[_RelationTarget]:
    if value is None:
        return ()
    if isinstance(value, str):
        parsed = _target_mapping_from_string(value)
        if parsed is not None:
            return (_target_from_mapping(parsed),)
        return (_RelationTarget(path=value, note_id=None, relation=None),)
    if isinstance(value, Mapping):
        return (_target_from_mapping(value),)
    if isinstance(value, Sequence):
        targets: list[_RelationTarget] = []
        for item in value:
            if isinstance(item, str):
                parsed = _target_mapping_from_string(item)
                if parsed is not None:
                    targets.append(_target_from_mapping(parsed))
                else:
                    targets.append(
                        _RelationTarget(path=item, note_id=None, relation=None)
                    )
            elif isinstance(item, Mapping):
                targets.append(_target_from_mapping(cast(JSONObject, item)))
        return targets
    return ()


def _target_mapping_from_string(value: str) -> Mapping[str, JSONValue] | None:
    if not value.lstrip().startswith("{"):
        return None
    try:
        parsed = ast.literal_eval(value)
    except (SyntaxError, ValueError):
        return None
    if not isinstance(parsed, Mapping):
        return None
    return cast(JSONObject, parsed)


def _target_from_mapping(value: Mapping[str, JSONValue]) -> _RelationTarget:
    path = _string_field(value, "path") or _string_field(value, "target_path")
    note_id = _string_field(value, "id") or _string_field(value, "target_note_id")
    relation_value = _string_field(value, "relation")
    relation = _relation_or_none(relation_value)
    return _RelationTarget(path=path, note_id=note_id, relation=relation)


def _string_field(value: Mapping[str, JSONValue], key: str) -> str | None:
    raw = value.get(key)
    return raw.strip() if isinstance(raw, str) and raw.strip() else None


def _relation_or_none(value: str | None) -> ObsidianRelationType | None:
    if value is None:
        return None
    try:
        return ObsidianRelationType(value)
    except ValueError:
        return None


def source_refs_from_json(value: JSONValue | None) -> list[JSONObject]:
    """Return relation objects from a dynamic JSON value.

    Args:
        value: Dynamic boundary value expected to contain source refs.

    Returns:
        JSON object refs with path/id when present.
    """
    if not isinstance(value, Sequence) or isinstance(value, str):
        return []
    return [dict(item) for item in value if isinstance(item, dict)]
