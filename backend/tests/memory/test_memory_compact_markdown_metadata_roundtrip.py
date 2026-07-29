"""Memory Compact Markdown metadata type round-trip tests."""

from __future__ import annotations

from app.memory.infrastructure.repositories.memory_compacts.obsidian_markdown_parser import (
    _read_frontmatter,
)
from app.memory.infrastructure.repositories.memory_compacts.obsidian_markdown_serializer import (
    _yaml_scalar,
)


def test_memory_compact_frontmatter_preserves_collection_metadata_types() -> None:
    """Block and inline YAML collections should parse as string tuples."""
    block_frontmatter, _ = _read_frontmatter(
        """---
alexandria_type: memory_compact
tags:
  - Alexandria
  - 'memory-compact'
---
Body
"""
    )
    inline_frontmatter, _ = _read_frontmatter(
        """---
alexandria_type: memory_compact
tags: [Alexandria, 'memory-compact']
---
Body
"""
    )

    assert block_frontmatter["tags"] == ("Alexandria", "memory-compact")
    assert inline_frontmatter["tags"] == ("Alexandria", "memory-compact")


def test_memory_compact_frontmatter_preserves_boolean_metadata_types() -> None:
    """Boolean metadata should remain Boolean through render and parse."""
    rendered_true = _yaml_scalar(True)
    rendered_false = _yaml_scalar(False)
    frontmatter, _ = _read_frontmatter(
        f"""---
alexandria_type: memory_compact
source_of_truth: {rendered_true}
requires_review: {rendered_false}
---
Body
"""
    )

    assert rendered_true == "true"
    assert rendered_false == "false"
    assert frontmatter["source_of_truth"] is True
    assert frontmatter["requires_review"] is False


def test_memory_compact_frontmatter_collection_render_parse_round_trip() -> None:
    """Rendered string collections should parse back without stringification."""
    rendered_tags = _yaml_scalar(("alpha", "beta"))
    frontmatter, _ = _read_frontmatter(
        f"""---
alexandria_type: memory_compact
tags: {rendered_tags}
---
Body
"""
    )

    assert rendered_tags == "['alpha', 'beta']"
    assert frontmatter["tags"] == ("alpha", "beta")
