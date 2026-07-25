"""Strict conflict resolution request schema for memory reconciliation."""

from __future__ import annotations

from app.memory.domain.event_enum.reconciliation_enums import (
    MemoryConflictStatus,
)
from app.shared.schemas.common_schemas import StrictSchemaModel
from app.shared.types.types_convert_utils import enum_value
from pydantic import Field, field_validator


class MemoryConflictResolutionRequest(StrictSchemaModel):
    """Explicit final resolution for one first-class memory conflict."""

    status: MemoryConflictStatus
    resolution: str = Field(min_length=1, max_length=10_000)

    @field_validator("status")
    @classmethod
    def require_resolved_status(
        cls,
        value: MemoryConflictStatus | str,
    ) -> MemoryConflictStatus:
        """Reject non-final conflict states at the HTTP boundary.

        Args:
            value: Value.

        Returns:
            MemoryConflictStatus: Operation result.
        """
        normalized = enum_value(value, MemoryConflictStatus, "status")
        if not normalized.value.startswith("RESOLVED_"):
            raise ValueError("memory conflict resolution requires a RESOLVED_* status")
        return normalized

    @field_validator("resolution")
    @classmethod
    def normalize_resolution(cls, value: str) -> str:
        """Normalize and require a concrete resolution explanation.

        Args:
            value: Value.

        Returns:
            str: Operation result.
        """
        normalized = value.strip()
        if not normalized:
            raise ValueError("memory conflict resolution is required")
        return normalized
