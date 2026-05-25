"""Enums for Obsidian-backed Alexandria notes."""

from __future__ import annotations

from enum import StrEnum


class AlexandriaNoteType(StrEnum):
    """Managed Alexandria Markdown note kinds."""

    CONTEXT = "context"
    MEMORY_COMPACT = "memory_compact"
    SKILL = "skill"
    PROMPT = "prompt"
    LIBRARIAN_BRIEF = "librarian_brief"
    LIBRARIAN_CHAT = "librarian_chat"
    JOB_PLAN = "job_plan"


class ObsidianIndexStatus(StrEnum):
    """Index lifecycle status for one vault note."""

    INDEXED = "indexed"
    STALE = "stale"
    ERROR = "error"
