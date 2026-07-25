"""Strict conflict response schemas for memory reconciliation."""

from __future__ import annotations

from app.memory.domain.entities.memory_reconciliation import (
    MemoryConflictSet,
)
from app.memory.domain.event_enum.context_enums import ContextScope
from app.memory.domain.event_enum.reconciliation_enums import (
    MemoryConflictStatus,
)
from app.shared.schemas.common_schemas import StrictSchemaModel
from app.shared.schemas.datetime_schemas import AwareTimestamp
from pydantic import TypeAdapter

_CONFLICT_ADAPTER = TypeAdapter(MemoryConflictSet)


class MemoryConflictResponse(StrictSchemaModel):
    """First-class unresolved or resolved memory conflict."""

    conflict_set_id: str
    context_ids: list[str]
    candidate_id: str
    subject_key: str
    claim_key: str
    scope: ContextScope
    validity_overlap: bool
    reason: str
    status: MemoryConflictStatus
    resolution: str | None
    created_at: AwareTimestamp
    resolved_at: AwareTimestamp | None

    @classmethod
    def from_entity(cls, value: MemoryConflictSet) -> MemoryConflictResponse:
        """Validate one conflict set as a strict HTTP response.

        Args:
            value: Value.

        Returns:
            MemoryConflictResponse: Operation result.
        """
        return cls.model_validate(_CONFLICT_ADAPTER.dump_python(value, mode="python"))


class MemoryConflictListResponse(StrictSchemaModel):
    """Paginated-style list of durable memory conflicts."""

    items: list[MemoryConflictResponse]
    total: int
