"""HTTP schemas for independently assessed platform capabilities."""

from __future__ import annotations

from pydantic import Field

from app.operations.domain.entities.operational_capability import (
    OperationalCapability,
    OperationalCapabilitySnapshot,
    OperationalCapabilityState,
)
from app.shared.schemas.common_schemas import StrictSchemaModel
from app.shared.schemas.datetime_schemas import AwareTimestamp


class OperationalCapabilityResponse(StrictSchemaModel):
    """One independently assessed platform capability."""

    state: OperationalCapabilityState
    ready: bool
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)

    @classmethod
    def from_entity(
        cls,
        item: OperationalCapability,
    ) -> OperationalCapabilityResponse:
        return cls(
            state=item.state,
            ready=item.ready,
            blockers=list(item.blockers),
            warnings=list(item.warnings),
        )


class OperationalCapabilitySnapshotResponse(StrictSchemaModel):
    """Core, semantic, and optional Librarian readiness."""

    checked_at: AwareTimestamp
    core_memory: OperationalCapabilityResponse
    semantic_retrieval: OperationalCapabilityResponse
    librarian: OperationalCapabilityResponse

    @classmethod
    def from_entity(
        cls,
        snapshot: OperationalCapabilitySnapshot,
    ) -> OperationalCapabilitySnapshotResponse:
        return cls(
            checked_at=snapshot.checked_at,
            core_memory=OperationalCapabilityResponse.from_entity(snapshot.core_memory),
            semantic_retrieval=OperationalCapabilityResponse.from_entity(
                snapshot.semantic_retrieval
            ),
            librarian=OperationalCapabilityResponse.from_entity(snapshot.librarian),
        )
