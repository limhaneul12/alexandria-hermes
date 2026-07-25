"""Strict HTTP request schema for existing-memory reconciliation scans."""

from __future__ import annotations

from app.memory.domain.contracts.memory_existing_reconciliation_contracts import (
    ExistingMemoryReconciliationRequest,
)
from app.memory.domain.event_enum.context_enums import ContextScope
from app.shared.schemas.common_schemas import StrictSchemaModel
from pydantic import Field, field_validator


class ExistingMemoryReconciliationHttpRequest(StrictSchemaModel):
    """Bounded filters for dry-run or apply existing-memory reconciliation."""

    project: str | None = Field(default=None, max_length=255)
    scope: ContextScope | None = None
    include_archived: bool = False
    max_contexts: int = Field(default=500, ge=1, le=10_000)
    batch_size: int = Field(default=100, ge=1, le=500)
    recall_limit: int = Field(default=20, ge=1, le=100)

    @field_validator("project")
    @classmethod
    def normalize_optional_project(cls, value: str | None) -> str | None:
        """Normalize optional project identity without inventing one.

        Args:
            value: Value.

        Returns:
            str | None: Operation result.
        """
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None

    def to_contract(self) -> ExistingMemoryReconciliationRequest:
        """Convert validated HTTP input into the internal frozen contract.

        Returns:
            ExistingMemoryReconciliationRequest: Operation result.
        """
        return ExistingMemoryReconciliationRequest(
            project=self.project,
            scope=self.scope,
            include_archived=self.include_archived,
            max_contexts=self.max_contexts,
            batch_size=self.batch_size,
            recall_limit=self.recall_limit,
        )
