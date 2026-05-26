"""State access helpers for Obsidian librarian LangGraph payloads."""

from __future__ import annotations

from collections.abc import Mapping

from app.obsidian.domain.event_enum.obsidian_enums import AlexandriaNoteType
from app.shared.types.extra_types import JSONObject, JSONValue

# Broad type justified: LangGraph TypedDict state is inferred as Mapping[str, object].
type StateLookup = Mapping[str, object]


def state_string(state: StateLookup, key: str) -> str:
    """Read a string state field or return an empty string.

    Args:
        state: Serialized LangGraph state.
        key: State key to read.

    Returns:
        String value, or an empty string.
    """
    value = state.get(key)
    return value if isinstance(value, str) else ""


def state_optional_string(state: StateLookup, key: str) -> str | None:
    """Read a non-empty optional string state field.

    Args:
        state: Serialized LangGraph state.
        key: State key to read.

    Returns:
        String value, or None when absent/empty.
    """
    value = state.get(key)
    return value if isinstance(value, str) and value else None


def state_object(state: StateLookup, key: str) -> JSONObject:
    """Read a JSON object state field.

    Args:
        state: Serialized LangGraph state.
        key: State key to read.

    Returns:
        JSON object value, or an empty object.
    """
    value = state.get(key)
    return dict(value) if isinstance(value, dict) else {}


def state_list(state: StateLookup, key: str) -> list[JSONValue]:
    """Read a JSON list state field.

    Args:
        state: Serialized LangGraph state.
        key: State key to read.

    Returns:
        JSON list value, or an empty list.
    """
    value = state.get(key)
    return list(value) if isinstance(value, list) else []


def state_string_list(state: StateLookup, key: str) -> list[str]:
    """Read a string list state field.

    Args:
        state: Serialized LangGraph state.
        key: State key to read.

    Returns:
        List containing only string items.
    """
    return [item for item in state_list(state, key) if isinstance(item, str)]


def state_json_object_list(state: StateLookup, key: str) -> list[JSONObject]:
    """Read a JSON object list state field.

    Args:
        state: Serialized LangGraph state.
        key: State key to read.

    Returns:
        List containing only JSON object items.
    """
    return [dict(item) for item in state_list(state, key) if isinstance(item, dict)]


def state_note_types(state: StateLookup) -> list[AlexandriaNoteType]:
    """Return requested note type filters from serialized state.

    Args:
        state: Serialized LangGraph state.

    Returns:
        Valid Alexandria note type filters.
    """
    note_types: list[AlexandriaNoteType] = []
    for value in state_string_list(state, "preferred_alexandria_types"):
        try:
            note_types.append(AlexandriaNoteType(value))
        except ValueError:
            continue
    return note_types


def state_int(state: StateLookup, key: str, default: int) -> int:
    """Return a positive int from serialized state, or a default.

    Args:
        state: Serialized LangGraph state.
        key: State key to read.
        default: Fallback value.

    Returns:
        Positive integer value, or the fallback.
    """
    value = state.get(key)
    if isinstance(value, int) and value > 0:
        return value
    return default
