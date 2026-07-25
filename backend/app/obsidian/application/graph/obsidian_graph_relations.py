"""Stable public facade for Obsidian graph relation parsing and rendering."""

from __future__ import annotations

from app.obsidian.application.graph.obsidian_graph_edge_builder import (
    relation_edges_from_note,
)
from app.obsidian.application.graph.obsidian_graph_link_renderer import (
    add_or_update_alexandria_links_section,
)
from app.obsidian.application.graph.obsidian_graph_relation_contracts import (
    ALEXANDRIA_LINKS_END,
    ALEXANDRIA_LINKS_START,
)
from app.obsidian.application.graph.obsidian_graph_relation_targets import (
    source_refs_from_json,
)

__all__ = (
    "ALEXANDRIA_LINKS_END",
    "ALEXANDRIA_LINKS_START",
    "add_or_update_alexandria_links_section",
    "relation_edges_from_note",
    "source_refs_from_json",
)
