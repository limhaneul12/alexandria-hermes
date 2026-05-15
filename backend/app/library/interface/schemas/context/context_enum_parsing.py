"""Enum parsers for Context Vault schema boundaries."""

from __future__ import annotations

from app.library.domain.event_enum.context_enums import (
    ContextContentFormat,
    ContextImportance,
    ContextKind,
    ContextSourceType,
    ContextStorageStatus,
    RagHealthState,
    RagStrategy,
)


# Broad type justified: Pydantic before validators receive raw boundary input.
def parse_context_kind_value(value: object) -> ContextKind | None:
    """Parse optional public JSON context kind values.

    Args:
        value: Raw boundary value.

    Returns:
        Parsed context kind when provided.
    """
    if value is None:
        return None
    if isinstance(value, ContextKind):
        return value
    if isinstance(value, str):
        return ContextKind(value)
    raise ValueError("kind must be a valid context kind")


# Broad type justified: Pydantic before validators receive raw boundary input.
def parse_content_format_value(value: object) -> ContextContentFormat:
    """Parse public JSON content format values.

    Args:
        value: Raw boundary value.

    Returns:
        Parsed content format.
    """
    if isinstance(value, ContextContentFormat):
        return value
    if isinstance(value, str):
        return ContextContentFormat(value)
    raise ValueError("content_format must be a valid content format")


# Broad type justified: Pydantic before validators receive raw boundary input.
def parse_source_type_value(value: object) -> ContextSourceType:
    """Parse public JSON source type values.

    Args:
        value: Raw boundary value.

    Returns:
        Parsed source type.
    """
    if isinstance(value, ContextSourceType):
        return value
    if isinstance(value, str):
        return ContextSourceType(value)
    raise ValueError("source_type must be a valid source type")


# Broad type justified: Pydantic before validators receive raw boundary input.
def parse_importance_value(value: object) -> ContextImportance:
    """Parse public JSON importance values.

    Args:
        value: Raw boundary value.

    Returns:
        Parsed importance.
    """
    if isinstance(value, ContextImportance):
        return value
    if isinstance(value, str):
        return ContextImportance(value)
    raise ValueError("importance must be a valid importance")


# Broad type justified: Pydantic before validators receive raw boundary input.
def parse_storage_status_value(value: object) -> ContextStorageStatus:
    """Parse public JSON storage status values.

    Args:
        value: Raw boundary value.

    Returns:
        Parsed storage status.
    """
    if isinstance(value, ContextStorageStatus):
        return value
    if isinstance(value, str):
        return ContextStorageStatus(value)
    raise ValueError("status must be a valid storage status")


# Broad type justified: Pydantic before validators receive raw boundary input.
def parse_rag_strategy_value(value: object) -> RagStrategy:
    """Parse public JSON RAG strategy values.

    Args:
        value: Raw boundary value.

    Returns:
        Parsed RAG strategy.
    """
    if isinstance(value, RagStrategy):
        return value
    if isinstance(value, str):
        return RagStrategy(value)
    raise ValueError("strategy must be a valid RAG strategy")


# Broad type justified: Pydantic before validators receive raw boundary input.
def parse_rag_health_state_value(value: object) -> RagHealthState:
    """Parse public JSON RAG health state values.

    Args:
        value: Raw boundary value.

    Returns:
        Parsed RAG health state.
    """
    if isinstance(value, RagHealthState):
        return value
    if isinstance(value, str):
        return RagHealthState(value)
    raise ValueError("health state must be a valid RAG health state")
