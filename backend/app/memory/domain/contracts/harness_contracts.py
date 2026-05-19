"""Agent-owned harness capture contracts."""

from __future__ import annotations

from dataclasses import dataclass, field

from app.memory.domain.event_enum.context_enums import ContextScope
from app.memory.domain.types.context_payload_types import ContextMetadataPayload


@dataclass(frozen=True, slots=True, kw_only=True)
class HarnessCapture:
    """Internal command for saving an agent execution harness."""

    task_goal: str
    reusable_procedure: str
    summary: str | None = None
    project: str | None = None
    scope: ContextScope = ContextScope.PROJECT
    workspace_id: str | None = None
    agent_id: str | None = None
    user_id: str | None = None
    session_id: str | None = None
    source_agent: str = "Hermes"
    environment: str | None = None
    trigger_context: str | None = None
    steps: list[str] = field(default_factory=list)
    commands: list[str] = field(default_factory=list)
    tests: list[str] = field(default_factory=list)
    failures: list[str] = field(default_factory=list)
    fixes: list[str] = field(default_factory=list)
    artifacts: list[str] = field(default_factory=list)
    recall_keywords: list[str] = field(default_factory=list)
    safety_notes: list[str] = field(default_factory=list)
    metadata: ContextMetadataPayload = field(default_factory=ContextMetadataPayload)
