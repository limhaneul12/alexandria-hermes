"""Memory and Context Vault CLI command contracts."""

from __future__ import annotations

from dataclasses import dataclass

from app.memory.domain.event_enum.context_enums import (
    ContextKind,
    ContextScope,
    RagStrategy,
)
from app.memory.domain.event_enum.memory_compact_enums import MemoryCompactStatus


@dataclass(frozen=True, slots=True, kw_only=True)
class ContextRecallCommand:
    """Parameters for context recall/RAG search."""

    query: str
    strategy: RagStrategy
    limit: int
    project: str | None
    kind: ContextKind | None
    include_scopes: list[ContextScope]
    workspace_id: str | None
    agent_id: str | None
    user_id: str | None
    session_id: str | None


@dataclass(frozen=True, slots=True, kw_only=True)
class ContextIdCommand:
    """Parameters for commands targeting one context."""

    context_id: str


@dataclass(frozen=True, slots=True, kw_only=True)
class HarnessListCommand:
    """Parameters for listing execution harness contexts."""

    project: str | None
    scope: ContextScope | None
    source_agent: str | None
    tag: str | None
    limit: int
    offset: int
    include_archived: bool


@dataclass(frozen=True, slots=True, kw_only=True)
class HarnessCaptureCommand:
    """Parameters for capturing or checking one execution harness."""

    task_goal: str
    reusable_procedure: str | None
    reusable_procedure_file: str | None
    summary: str | None
    project: str | None
    scope: ContextScope
    source_agent: str
    environment: str | None
    trigger_context: str | None
    steps: list[str]
    commands: list[str]
    tests: list[str]
    failures: list[str]
    fixes: list[str]
    artifacts: list[str]
    recall_keywords: list[str]
    safety_notes: list[str]


@dataclass(frozen=True, slots=True, kw_only=True)
class ContextReindexCommand:
    """Parameters for rebuilding context embeddings."""

    limit: int
    force: bool


@dataclass(frozen=True, slots=True, kw_only=True)
class MemoryCompactListCommand:
    """Parameters for listing durable Memory Compact artifacts."""

    project: str | None
    status: MemoryCompactStatus | None
    limit: int
    offset: int


@dataclass(frozen=True, slots=True, kw_only=True)
class MemoryCompactIdCommand:
    """Parameters for commands targeting one Memory Compact."""

    compact_id: str


@dataclass(frozen=True, slots=True, kw_only=True)
class ContextCompactCommand:
    """Parameters for preparing a compact handoff context."""

    current_goal: str
    completed: list[str]
    in_progress: list[str]
    key_decisions: list[str]
    next_actions: list[str]
    risks: list[str]
    project: str | None
    scope: ContextScope
    workspace_id: str | None
    agent_id: str | None
    user_id: str | None
    session_id: str | None
    visibility: ContextScope
    source_agent: str


@dataclass(frozen=True, slots=True, kw_only=True)
class ContextMemoryMapCommand:
    """Parameters for building a project memory map."""

    project: str | None
    limit: int
    include_archived: bool


@dataclass(frozen=True, slots=True, kw_only=True)
class ContextCurateCommand:
    """Parameters for listing curation candidates."""

    project: str | None
    stale_after_days: int
    limit: int
