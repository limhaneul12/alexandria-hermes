"""Strict temporal recall response schemas for memory reconciliation."""

from __future__ import annotations

from app.memory.domain.entities.memory_reconciliation import (
    MemoryTemporalRecallPack,
    MemoryTemporalState,
)
from app.memory.domain.event_enum.reconciliation_enums import (
    MemoryTemporalRecallMode,
)
from app.memory.interface.schemas.context.context_mapping import match_payload
from app.memory.interface.schemas.context.context_schema import (
    ContextSearchMatchResponse,
)
from app.shared.schemas.common_schemas import StrictSchemaModel
from app.shared.schemas.datetime_schemas import AwareTimestamp
from pydantic import TypeAdapter

_TEMPORAL_ADAPTER = TypeAdapter(MemoryTemporalState)


class MemoryTemporalStateResponse(StrictSchemaModel):
    """Temporal and reconciliation overlay attached to one Context match."""

    context_id: str
    recorded_at: AwareTimestamp
    observed_at: AwareTimestamp | None
    valid_from: AwareTimestamp | None
    valid_to: AwareTimestamp | None
    is_current: bool
    conflict_set_ids: list[str]
    superseded_by: list[str]
    supersedes: list[str]
    relation_summary: list[str]


class MemoryTemporalRecallMatchResponse(StrictSchemaModel):
    """One ranked Context match with current/historical memory metadata."""

    match: ContextSearchMatchResponse
    temporal_state: MemoryTemporalStateResponse | None
    is_current: bool
    conflict_set_ids: list[str]
    superseded_by: list[str]
    supersedes: list[str]
    relation_summary: list[str]


class MemoryTemporalRecallResponse(StrictSchemaModel):
    """Context recall result filtered through an explicit temporal perspective."""

    query: str
    mode: MemoryTemporalRecallMode
    as_of: AwareTimestamp | None
    strategy: str
    effective_strategy: str
    warnings: list[str]
    recall_scopes: list[str]
    matches: list[MemoryTemporalRecallMatchResponse]
    context_pack: str

    @classmethod
    def from_entity(
        cls,
        value: MemoryTemporalRecallPack,
    ) -> MemoryTemporalRecallResponse:
        """Validate one temporal recall result as a strict HTTP response.

        Args:
            value: Value.

        Returns:
            MemoryTemporalRecallResponse: Operation result.
        """
        matches = [
            MemoryTemporalRecallMatchResponse(
                match=match_payload(item.match),
                temporal_state=(
                    None
                    if item.temporal_state is None
                    else MemoryTemporalStateResponse.model_validate(
                        _TEMPORAL_ADAPTER.dump_python(
                            item.temporal_state,
                            mode="python",
                        )
                    )
                ),
                is_current=item.is_current,
                conflict_set_ids=list(item.conflict_set_ids),
                superseded_by=list(item.superseded_by),
                supersedes=list(item.supersedes),
                relation_summary=list(item.relation_summary),
            )
            for item in value.matches
        ]
        return cls(
            query=value.query,
            mode=value.mode,
            as_of=value.as_of,
            strategy=value.strategy.value,
            effective_strategy=value.effective_strategy.value,
            warnings=list(value.warnings),
            recall_scopes=[item.value for item in value.recall_scopes],
            matches=matches,
            context_pack=value.context_pack,
        )
