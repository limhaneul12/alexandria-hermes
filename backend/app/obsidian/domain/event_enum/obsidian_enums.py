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
    IMPLEMENTATION_HISTORY = "implementation_history"


class ObsidianIndexStatus(StrEnum):
    """Index lifecycle status for one vault note."""

    INDEXED = "indexed"
    STALE = "stale"
    ERROR = "error"


class ObsidianRelationType(StrEnum):
    """Supported Alexandria graph relation kinds."""

    CITES = "cites"
    DERIVED_FROM = "derived_from"
    RELATED = "related"
    SUPERSEDES = "supersedes"
    PROMOTES_TO = "promotes_to"
    BLOCKS = "blocks"
    RESOLVES = "resolves"
    WIKILINK = "wikilink"


class ObsidianEdgeSourceKind(StrEnum):
    """Where an indexed graph edge came from."""

    FRONTMATTER = "frontmatter"
    WIKILINK = "wikilink"
    INFERRED = "inferred"
    USER_APPROVED = "user_approved"


class ObsidianLibrarianWorkflowStatus(StrEnum):
    """Status values for Obsidian librarian approval workflows."""

    WAITING_FOR_APPROVAL = "waiting_for_approval"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class ObsidianLibrarianJobStatus(StrEnum):
    """Status values for asynchronous Obsidian librarian execution jobs."""

    PENDING = "pending"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
