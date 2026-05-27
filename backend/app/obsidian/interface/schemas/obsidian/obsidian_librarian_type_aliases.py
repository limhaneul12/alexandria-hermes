"""Type alias normalization for Obsidian librarian request schemas."""

from __future__ import annotations

from app.obsidian.domain.event_enum.obsidian_enums import AlexandriaNoteType
from app.shared.types.extra_types import JSONValue


def preferred_note_type_input(value: JSONValue) -> JSONValue:
    """Normalize agent-facing note type aliases before enum validation.

    Args:
        value: Raw note type filter item supplied by an MCP or HTTP caller.

    Returns:
        Normalized note type value for downstream enum validation.
    """
    if not isinstance(value, str):
        return value
    normalized = value.strip().casefold().replace("-", "_").replace(" ", "_")
    aliases = {
        "index": AlexandriaNoteType.CONTEXT.value,
        "indexes": AlexandriaNoteType.CONTEXT.value,
        "indices": AlexandriaNoteType.CONTEXT.value,
        "memory": AlexandriaNoteType.MEMORY_COMPACT.value,
        "memory_compact": AlexandriaNoteType.MEMORY_COMPACT.value,
        "memory_compacts": AlexandriaNoteType.MEMORY_COMPACT.value,
    }
    return aliases.get(normalized, normalized)
