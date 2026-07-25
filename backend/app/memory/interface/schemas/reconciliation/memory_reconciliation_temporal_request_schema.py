"""Strict temporal recall request schema for memory reconciliation."""

from __future__ import annotations

from app.memory.domain.contracts.memory_reconciliation_contracts import (
    MemoryTemporalRecallRequest,
)
from app.memory.domain.event_enum.context_enums import (
    ContextKind,
    ContextRecallLifecycleStatus,
    ContextScope,
    RagStrategy,
)
from app.memory.domain.event_enum.reconciliation_enums import (
    MemoryTemporalRecallMode,
)
from app.shared.schemas.common_schemas import StrictSchemaModel
from app.shared.schemas.datetime_schemas import AwareTimestamp
from app.shared.types.types_convert_utils import enum_value
from pydantic import Field, field_validator


class MemoryTemporalRecallHttpRequest(StrictSchemaModel):
    """Recall Contexts through current, historical, or all temporal state."""

    query: str = Field(min_length=1, max_length=10_000)
    mode: MemoryTemporalRecallMode = MemoryTemporalRecallMode.CURRENT
    as_of: AwareTimestamp | None = None
    strategy: RagStrategy = RagStrategy.HYBRID
    limit: int = Field(default=5, ge=1, le=100)
    project: str | None = Field(default=None, max_length=1000)
    kind: ContextKind | None = None
    include_scopes: list[ContextScope] = Field(default_factory=list)
    workspace_id: str | None = Field(default=None, max_length=1000)
    agent_id: str | None = Field(default=None, max_length=1000)
    user_id: str | None = Field(default=None, max_length=1000)
    session_id: str | None = Field(default=None, max_length=1000)
    include_lifecycle_statuses: list[ContextRecallLifecycleStatus] = Field(
        default_factory=list
    )

    @field_validator("query")
    @classmethod
    def normalize_query(cls, value: str) -> str:
        """Normalize and require a concrete recall query.

        Args:
            value: Value.

        Returns:
            str: Operation result.
        """
        normalized = value.strip()
        if not normalized:
            raise ValueError("temporal recall query is required")
        return normalized

    @field_validator(
        "project",
        "workspace_id",
        "agent_id",
        "user_id",
        "session_id",
    )
    @classmethod
    def normalize_temporal_identity(cls, value: str | None) -> str | None:
        """Normalize optional temporal recall identities.

        Args:
            value: Value.

        Returns:
            str | None: Operation result.
        """
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None

    def to_contract(self) -> MemoryTemporalRecallRequest:
        """Convert the HTTP request into the temporal recall application contract.

        Returns:
            MemoryTemporalRecallRequest: Operation result.
        """
        return MemoryTemporalRecallRequest(
            query=self.query,
            mode=enum_value(self.mode, MemoryTemporalRecallMode, "mode"),
            as_of=self.as_of,
            strategy=enum_value(self.strategy, RagStrategy, "strategy"),
            limit=self.limit,
            project=self.project,
            kind=(
                None
                if self.kind is None
                else enum_value(self.kind, ContextKind, "kind")
            ),
            include_scopes=tuple(
                enum_value(item, ContextScope, "include_scopes")
                for item in self.include_scopes
            ),
            workspace_id=self.workspace_id,
            agent_id=self.agent_id,
            user_id=self.user_id,
            session_id=self.session_id,
            include_lifecycle_statuses=tuple(
                enum_value(
                    item,
                    ContextRecallLifecycleStatus,
                    "include_lifecycle_statuses",
                )
                for item in self.include_lifecycle_statuses
            ),
        )
