"""Domain enums for Alexandria-Hermes backend models."""

from __future__ import annotations

from enum import StrEnum


class ItemType(StrEnum):
    """Library item top-level type."""

    SKILL = "SKILL"
    WORKFLOW = "WORKFLOW"
    KNOWLEDGE = "KNOWLEDGE"


class ItemStatus(StrEnum):
    """Item publishing state."""

    DRAFT = "DRAFT"
    ACTIVE = "ACTIVE"
    ARCHIVED = "ARCHIVED"
    DEPRECATED = "DEPRECATED"


class SourceType(StrEnum):
    """Source system for library item creation."""

    USER_CREATED = "USER_CREATED"
    AGENT_SUBMITTED = "AGENT_SUBMITTED"
    LIBRARIAN_CREATED = "LIBRARIAN_CREATED"
    IMPORTED = "IMPORTED"


class CreatedByType(StrEnum):
    """Creator authority for lifecycle fields."""

    USER = "USER"
    AGENT = "AGENT"
    LIBRARIAN = "LIBRARIAN"


class SelectionSource(StrEnum):
    """How an item was chosen by an agent."""

    RECOMMENDATION = "RECOMMENDATION"
    MANUAL_BROWSE = "MANUAL_BROWSE"
    SEARCH = "SEARCH"
    DIRECT_LINK = "DIRECT_LINK"


class ProviderType(StrEnum):
    """Librarian provider implementation type."""

    OPENAI = "OPENAI"
    OPENROUTER = "OPENROUTER"
    ANTHROPIC = "ANTHROPIC"
    HERMES = "HERMES"
    LOCAL = "LOCAL"
    CUSTOM = "CUSTOM"


class AuthType(StrEnum):
    """Authentication mode used by a librarian provider."""

    API_KEY = "API_KEY"
    OAUTH = "OAUTH"
    NONE = "NONE"


class RiskLevel(StrEnum):
    """Skill risk level classification."""

    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
