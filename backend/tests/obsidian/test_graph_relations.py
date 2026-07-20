"""Obsidian graph relation parsing behavior tests."""

from __future__ import annotations

from app.obsidian.application.graph.obsidian_graph_relations import (
    add_or_update_alexandria_links_section,
    relation_edges_from_note,
)
from app.obsidian.domain.event_enum.obsidian_enums import (
    ObsidianEdgeSourceKind,
    ObsidianRelationType,
)


def test_graph_relations_parse_frontmatter_and_wikilinks() -> None:
    """Frontmatter relations and body wikilinks should become rebuildable edges."""
    edges = relation_edges_from_note(
        note_id="ctx_current",
        relative_path="Alexandria/Contexts/Current.md",
        alexandria_root="Alexandria",
        frontmatter={
            "source_refs": [
                {
                    "id": "alexandria_start_here",
                    "path": "START_HERE.md",
                    "relation": "cites",
                }
            ],
            "related": ["Skills/Active/Web Research.md"],
        },
        body="Read [[Prompts/System/Research|research prompt]] and [[START_HERE]].",
    )

    actual = sorted(
        [
            (edge.target_note_id, edge.target_path, edge.relation, edge.source_kind)
            for edge in edges
        ],
        key=lambda item: (item[1], item[2].value, item[3].value, item[0] or ""),
    )
    assert actual == [
        (
            None,
            "Alexandria/Prompts/System/Research.md",
            ObsidianRelationType.WIKILINK,
            ObsidianEdgeSourceKind.WIKILINK,
        ),
        (
            "alexandria_start_here",
            "Alexandria/START_HERE.md",
            ObsidianRelationType.CITES,
            ObsidianEdgeSourceKind.FRONTMATTER,
        ),
        (
            None,
            "Alexandria/START_HERE.md",
            ObsidianRelationType.WIKILINK,
            ObsidianEdgeSourceKind.WIKILINK,
        ),
        (
            None,
            "Alexandria/Skills/Active/Web Research.md",
            ObsidianRelationType.RELATED,
            ObsidianEdgeSourceKind.FRONTMATTER,
        ),
    ]


def test_graph_relations_keep_vault_root_targets_when_root_is_dot() -> None:
    """Root-vault installs should not treat the first folder as Alexandria root."""
    edges = relation_edges_from_note(
        note_id="ctx_current",
        relative_path="Contexts/Current.md",
        alexandria_root=".",
        frontmatter={
            "source_refs": [
                {
                    "id": "alexandria_start_here",
                    "path": "START_HERE.md",
                    "relation": "cites",
                }
            ],
        },
        body="Read [[START_HERE]].",
    )

    actual = sorted(
        [
            (edge.target_note_id, edge.target_path, edge.relation, edge.source_kind)
            for edge in edges
        ],
        key=lambda item: (item[1], item[2].value, item[3].value, item[0] or ""),
    )
    assert actual == [
        (
            "alexandria_start_here",
            "START_HERE.md",
            ObsidianRelationType.CITES,
            ObsidianEdgeSourceKind.FRONTMATTER,
        ),
        (
            None,
            "START_HERE.md",
            ObsidianRelationType.WIKILINK,
            ObsidianEdgeSourceKind.WIKILINK,
        ),
    ]


def test_alexandria_links_section_updates_marker_without_touching_user_body() -> None:
    """Generated graph wikilinks should only replace the managed marker block."""
    body = "# Note\n\nUser paragraph.\n\n<!-- ALEXANDRIA-LINKS:START -->\nold\n<!-- ALEXANDRIA-LINKS:END -->\n"

    updated = add_or_update_alexandria_links_section(
        body,
        {
            "source_refs": [
                {"path": "START_HERE.md", "relation": "cites"},
            ]
        },
    )

    assert "User paragraph." in updated
    assert "old" not in updated
    assert "[[START_HERE]] — cites" in updated
