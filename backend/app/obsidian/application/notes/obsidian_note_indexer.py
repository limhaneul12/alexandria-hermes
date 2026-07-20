"""Build Obsidian note index payloads from Markdown files."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from app.obsidian.application.graph.obsidian_graph_relations import (
    relation_edges_from_note,
)
from app.obsidian.application.notes.obsidian_note_templates import (
    chunks_for_body,
    sha256_text,
    title_from_document,
)
from app.obsidian.domain.contracts.obsidian_contracts import ObsidianNoteIndex
from app.obsidian.domain.event_enum.obsidian_enums import AlexandriaNoteType
from app.obsidian.domain.obsidian_note_type_aliases import (
    normalized_alexandria_note_type,
)
from app.obsidian.infrastructure.markdown.frontmatter import (
    frontmatter_json,
    frontmatter_list,
    frontmatter_text,
    parse_markdown_document,
)


def note_index_from_path(
    path: Path,
    relative_path: str,
    *,
    alexandria_root: str,
) -> ObsidianNoteIndex | None:
    """Read one Markdown file and build an index payload when managed.

    Args:
        path: Absolute Markdown path.
        relative_path: Vault-relative Markdown path.
        alexandria_root: Managed Alexandria root, or "." when the vault is root.

    Returns:
        Index payload, or None when Alexandria frontmatter is missing.
    """
    text = path.read_text(encoding="utf-8")
    document = parse_markdown_document(text)
    note_type = _note_type_from_frontmatter(document.frontmatter)
    note_id = frontmatter_text(document.frontmatter, "id")
    if note_type is None or not note_id:
        return None
    stat = path.stat()
    body = document.body.rstrip("\n")
    frontmatter = frontmatter_json(document.frontmatter)
    frontmatter["alexandria_type"] = note_type.value
    return ObsidianNoteIndex(
        note_id=note_id,
        relative_path=relative_path,
        alexandria_type=note_type,
        title=title_from_document(document.frontmatter, body, path),
        status=frontmatter_text(document.frontmatter, "status") or "active",
        tags=frontmatter_list(document.frontmatter, "tags"),
        project=frontmatter_text(document.frontmatter, "project"),
        source=frontmatter_text(document.frontmatter, "source"),
        content_hash=sha256_text(text),
        frontmatter=frontmatter,
        body=body,
        size_bytes=stat.st_size,
        modified_at=datetime.fromtimestamp(stat.st_mtime, tz=UTC),
        chunks=chunks_for_body(body),
        edges=relation_edges_from_note(
            note_id=note_id,
            relative_path=relative_path,
            alexandria_root=alexandria_root,
            frontmatter=frontmatter,
            body=body,
        ),
    )


def _note_type_from_frontmatter(
    frontmatter: dict[str, str | list[str] | None],
) -> AlexandriaNoteType | None:
    explicit_value = frontmatter_text(frontmatter, "alexandria_type")
    if explicit_value:
        note_type = normalized_alexandria_note_type(explicit_value)
        if note_type is None:
            raise ValueError(f"invalid alexandria_type: {explicit_value}")
        return note_type
    for key in ("type", "item_type"):
        note_type = normalized_alexandria_note_type(frontmatter_text(frontmatter, key))
        if note_type is not None:
            return note_type
    return None
