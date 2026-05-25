"""Skill artifact status enum used by librarian acquisition contracts."""

from __future__ import annotations

from enum import StrEnum


class ItemStatus(StrEnum):
    """Publication state for a generated skill artifact."""

    DRAFT = "DRAFT"
    NEEDS_REVIEW = "NEEDS_REVIEW"
    ACTIVE = "ACTIVE"
    ARCHIVED = "ARCHIVED"
    DEPRECATED = "DEPRECATED"
    SUPERSEDED = "SUPERSEDED"
