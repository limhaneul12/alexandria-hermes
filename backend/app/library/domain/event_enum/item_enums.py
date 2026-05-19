"""Item concept enum definitions."""

from __future__ import annotations

from enum import StrEnum


class ItemType(StrEnum):
    """Library item top-level type."""

    SKILL = "SKILL"
    PROMPT = "PROMPT"


class ItemStatus(StrEnum):
    """Item publishing state."""

    DRAFT = "DRAFT"
    NEEDS_REVIEW = "NEEDS_REVIEW"
    ACTIVE = "ACTIVE"
    ARCHIVED = "ARCHIVED"
    DEPRECATED = "DEPRECATED"
    SUPERSEDED = "SUPERSEDED"


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


class LibraryItemPatchField(StrEnum):
    """Public base fields accepted by item-family patch payloads."""

    TITLE = "title"
    SUMMARY = "summary"
    CONTENT = "content"
    CATEGORY_ID = "category_id"
    TAGS = "tags"
    STATUS = "status"
