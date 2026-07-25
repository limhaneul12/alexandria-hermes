"""Application input contracts for existing-memory reconciliation."""

from __future__ import annotations

from dataclasses import dataclass

from app.memory.domain.event_enum.context_enums import ContextScope


@dataclass(frozen=True, slots=True, kw_only=True)
class ExistingMemoryReconciliationRequest:
    """Filters and safety bounds for an existing-memory reconciliation scan."""

    project: str | None = None
    scope: ContextScope | None = None
    include_archived: bool = False
    max_contexts: int = 500
    batch_size: int = 100
    recall_limit: int = 20
