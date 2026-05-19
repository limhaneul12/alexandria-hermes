"""Agent-owned harness payload contracts."""

from __future__ import annotations

from typing_extensions import TypedDict


class HarnessExecutionMetadataPayload(TypedDict, closed=True):
    """Persistent metadata for one agent execution harness."""

    task_goal: str
    environment: str | None
    trigger_context: str | None
    steps: list[str]
    commands: list[str]
    tests: list[str]
    failures: list[str]
    fixes: list[str]
    artifacts: list[str]
    reusable_procedure: str
    recall_keywords: list[str]
    safety_notes: list[str]
