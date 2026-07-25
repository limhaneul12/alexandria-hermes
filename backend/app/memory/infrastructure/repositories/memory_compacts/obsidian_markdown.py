"""Stable public facade for Obsidian-backed Memory Compact Markdown."""

from __future__ import annotations

from app.memory.infrastructure.repositories.memory_compacts.obsidian_markdown_contracts import (
    NOTE_SUFFIX,
)
from app.memory.infrastructure.repositories.memory_compacts.obsidian_markdown_parser import (
    read_compact_file,
)
from app.memory.infrastructure.repositories.memory_compacts.obsidian_markdown_path_policy import (
    is_safe_note_id,
    resolve_base_dir,
)
from app.memory.infrastructure.repositories.memory_compacts.obsidian_markdown_serializer import (
    serialize_compact,
)

__all__ = (
    "NOTE_SUFFIX",
    "is_safe_note_id",
    "read_compact_file",
    "resolve_base_dir",
    "serialize_compact",
)
