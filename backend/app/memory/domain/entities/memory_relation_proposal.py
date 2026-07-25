"""Model-assisted proposal entity for uncertain memory relations."""

from __future__ import annotations

from dataclasses import dataclass

from app.memory.domain.event_enum.reconciliation_enums import MemoryRelationType


@dataclass(frozen=True, slots=True, kw_only=True)
class MemoryRelationModelProposal:
    """Untrusted relation proposal produced by an external reasoning model."""

    relation: MemoryRelationType
    confidence: float
    reason: str
