"""Graph relation parsing and Alexandria wikilink section rendering."""

from __future__ import annotations

import ast
import hashlib
import re
from collections.abc import Iterable, Mapping, Sequence
from pathlib import PurePosixPath
from typing import cast

from app.obsidian.domain.contracts.obsidian_contracts import ObsidianEdgeIndex
from app.obsidian.domain.event_enum.obsidian_enums import (
    ObsidianEdgeSourceKind,
    ObsidianRelationType,
)
from app.shared.types.extra_types import JSONObject, JSONValue

ALEXANDRIA_LINKS_START = "<!-- ALEXANDRIA-LINKS:START -->"
ALEXANDRIA_LINKS_END = "<!-- ALEXANDRIA-LINKS:END -->"

_WIKILINK_RE = re.compile(r"\[\[([^\]|#]+)(?:#[^\]|]+)?(?:\|[^\]]+)?\]\]")
_FRONTMATTER_RELATIONS: tuple[tuple[str, ObsidianRelationType], ...] = (
    ("source_refs", ObsidianRelationType.CITES),
    ("derived_from", ObsidianRelationType.DERIVED_FROM),
    ("related", ObsidianRelationType.RELATED),
    ("supersedes", ObsidianRelationType.SUPERSEDES),
    ("promotes_to", ObsidianRelationType.PROMOTES_TO),
    ("blocks", ObsidianRelationType.BLOCKS),
    ("resolves", ObsidianRelationType.RESOLVES),
)
_ROOT_RELATIVE_LINK_PREFIXES = frozenset(
    {
        "Archive",
        "Contexts",
        "Indexes",
        "Memory Compacts",
        "Prompts",
        "Skills",
        "START_HERE.md",
        "_Inbox",
        "_Ops",
    }
)
_RELATION_HEADINGS: dict[ObsidianRelationType, str] = {
    ObsidianRelationType.CITES: "Sources",
    ObsidianRelationType.RELATED: "Related",
    ObsidianRelationType.DERIVED_FROM: "Derived From",
    ObsidianRelationType.SUPERSEDES: "Supersedes",
    ObsidianRelationType.PROMOTES_TO: "Promotes To",
    ObsidianRelationType.BLOCKS: "Blocks",
    ObsidianRelationType.RESOLVES: "Resolves",
}


def relation_edges_from_note(
    *,
    note_id: str,
    relative_path: str,
    alexandria_root: str,
    frontmatter: JSONObject,
    body: str,
) -> list[ObsidianEdgeIndex]:
    """Parse frontmatter relation fields and body wikilinks into edge indexes.

    Args:
        note_id: Stable source note id.
        relative_path: Vault-relative source path.
        alexandria_root: Managed Alexandria root, or "." when the vault is root.
        frontmatter: Parsed Markdown frontmatter.
        body: Markdown body text.

    Returns:
        Deduplicated graph edges for repository indexing.
    """
    edges: list[ObsidianEdgeIndex] = []
    seen: set[tuple[str, str, str, str | None]] = set()
    for field_name, fallback_relation in _FRONTMATTER_RELATIONS:
        for target in _relation_targets(frontmatter.get(field_name)):
            relation = target.relation or fallback_relation
            target_path = _normalize_target_path(
                target.path,
                alexandria_root=alexandria_root,
            )
            if target_path is None:
                continue
            key = (
                target_path,
                relation.value,
                ObsidianEdgeSourceKind.FRONTMATTER.value,
                target.note_id,
            )
            if key in seen:
                continue
            seen.add(key)
            edges.append(
                _edge(
                    source_note_id=note_id,
                    source_path=relative_path,
                    target_note_id=target.note_id,
                    target_path=target_path,
                    relation=relation,
                    source_kind=ObsidianEdgeSourceKind.FRONTMATTER,
                    confidence=1.0,
                )
            )
    for target_path in _wikilink_targets(
        body,
        relative_path=relative_path,
        alexandria_root=alexandria_root,
    ):
        if target_path == relative_path:
            continue
        key = (
            target_path,
            ObsidianRelationType.WIKILINK.value,
            ObsidianEdgeSourceKind.WIKILINK.value,
            None,
        )
        if key in seen:
            continue
        seen.add(key)
        edges.append(
            _edge(
                source_note_id=note_id,
                source_path=relative_path,
                target_note_id=None,
                target_path=target_path,
                relation=ObsidianRelationType.WIKILINK,
                source_kind=ObsidianEdgeSourceKind.WIKILINK,
                confidence=0.5,
            )
        )
    return edges


def add_or_update_alexandria_links_section(body: str, frontmatter: JSONObject) -> str:
    """Render relation frontmatter as a managed body wikilink section.

    Args:
        body: Existing Markdown body.
        frontmatter: Note frontmatter containing relation fields.

    Returns:
        Body with the managed Alexandria Links section updated or appended.
    """
    section = _render_links_section(frontmatter)
    if not section:
        return body
    block = f"{ALEXANDRIA_LINKS_START}\n{section}\n{ALEXANDRIA_LINKS_END}"
    pattern = re.compile(
        rf"\n?{re.escape(ALEXANDRIA_LINKS_START)}.*?{re.escape(ALEXANDRIA_LINKS_END)}",
        re.DOTALL,
    )
    if pattern.search(body):
        return pattern.sub(f"\n\n{block}", body).strip() + "\n"
    return f"{body.rstrip()}\n\n{block}\n" if body.strip() else f"{block}\n"


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


def _wikilink_targets(
    body: str,
    *,
    relative_path: str,
    alexandria_root: str,
) -> list[str]:
    targets: list[str] = []
    for match in _WIKILINK_RE.finditer(body):
        target = _normalize_wikilink_target_path(
            match.group(1),
            relative_path=relative_path,
            alexandria_root=alexandria_root,
        )
        if target is not None:
            targets.append(target)
    return targets


def _normalize_wikilink_target_path(
    path: str | None,
    *,
    relative_path: str,
    alexandria_root: str,
) -> str | None:
    normalized = _normalize_markdown_target(path)
    if normalized is None:
        return None
    root = alexandria_root.strip().strip("/") or "."
    first_segment = normalized.split("/", maxsplit=1)[0]
    if root != "." and normalized.startswith(f"{root}/"):
        return normalized
    if first_segment in _ROOT_RELATIVE_LINK_PREFIXES:
        return normalized if root == "." else f"{root}/{normalized}"
    source_parent = PurePosixPath(relative_path).parent
    return str(source_parent / normalized)


def _normalize_target_path(path: str | None, *, alexandria_root: str) -> str | None:
    normalized = _normalize_markdown_target(path)
    if normalized is None:
        return None
    root = alexandria_root.strip().strip("/") or "."
    if root == ".":
        return normalized
    if "/" in normalized:
        if normalized.startswith(f"{root}/"):
            return normalized
        return f"{root}/{normalized}"
    return f"{root}/{normalized}"


def _normalize_markdown_target(path: str | None) -> str | None:
    if path is None:
        return None
    normalized = path.strip().removeprefix("./")
    if not normalized or "://" in normalized or normalized.startswith("#"):
        return None
    normalized = normalized.removesuffix(".md") + ".md"
    if normalized.startswith("/") or ".." in normalized.split("/"):
        return None
    return normalized


def _edge(
    *,
    source_note_id: str,
    source_path: str,
    target_note_id: str | None,
    target_path: str,
    relation: ObsidianRelationType,
    source_kind: ObsidianEdgeSourceKind,
    confidence: float,
) -> ObsidianEdgeIndex:
    edge_key = "|".join(
        [
            source_note_id,
            source_path,
            target_note_id or "",
            target_path,
            relation.value,
            source_kind.value,
        ]
    )
    return ObsidianEdgeIndex(
        edge_id=hashlib.sha256(edge_key.encode("utf-8")).hexdigest(),
        source_note_id=source_note_id,
        source_path=source_path,
        target_note_id=target_note_id,
        target_path=target_path,
        relation=relation,
        confidence=confidence,
        source_kind=source_kind,
    )


def _render_links_section(frontmatter: JSONObject) -> str:
    sections: list[str] = ["## Alexandria Links"]
    relation_lines = 0
    for field_name, relation in _FRONTMATTER_RELATIONS:
        targets = list(_relation_targets(frontmatter.get(field_name)))
        if not targets:
            continue
        lines: list[str] = []
        for target in targets:
            if target.path is None:
                continue
            link_target = target.path.strip().removesuffix(".md")
            relation_text = (target.relation or relation).value
            lines.append(f"- [[{link_target}]] — {relation_text}")
        if not lines:
            continue
        sections.extend(["", f"### {_RELATION_HEADINGS[relation]}", *lines])
        relation_lines += len(lines)
    return "\n".join(sections) if relation_lines else ""
