"""Schemas for Memory Compact HTTP boundaries."""

from __future__ import annotations

from app.memory.domain.entities.memory_compact import (
    MemoryCompact,
    MemoryCompactSourceRef,
)
from app.memory.domain.event_enum.memory_compact_enums import (
    MemoryCompactStatus,
)
from app.memory.domain.repositories.memory_compact_repository import (
    MemoryCompactCreate,
    MemoryCompactSourceRefCreate,
)
from app.shared.schemas.common_schemas import StrictSchemaModel
from app.shared.schemas.datetime_schemas import AwareTimestamp
from pydantic import Field


class MemoryCompactSourceRefRequest(StrictSchemaModel):
    """Request schema for a compact source reference."""

    source_type: str = Field(min_length=1)
    source_id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    detail_path: str = Field(min_length=1)

    def to_create(self) -> MemoryCompactSourceRefCreate:
        """Convert request schema to service contract.

        Returns:
            Repository source-reference creation contract.
        """
        return MemoryCompactSourceRefCreate(
            source_type=self.source_type,
            source_id=self.source_id,
            title=self.title,
            detail_path=self.detail_path,
        )


class MemoryCompactCreateRequest(StrictSchemaModel):
    """Request schema for creating a Memory Compact."""

    project: str | None = None
    covered_from: AwareTimestamp
    covered_to: AwareTimestamp
    markdown_body: str = Field(min_length=1)
    status: MemoryCompactStatus = MemoryCompactStatus.DRAFT
    source_refs: list[MemoryCompactSourceRefRequest] = Field(default_factory=list)

    def to_create(self) -> MemoryCompactCreate:
        """Convert request schema to service contract.

        Returns:
            Repository creation contract.
        """
        return MemoryCompactCreate(
            project=self.project,
            covered_from=self.covered_from,
            covered_to=self.covered_to,
            markdown_body=self.markdown_body,
            status=MemoryCompactStatus(self.status),
            source_refs=[source_ref.to_create() for source_ref in self.source_refs],
        )


class MemoryCompactSourceRefResponse(StrictSchemaModel):
    """Response schema for compact source references."""

    id: str
    compact_id: str
    source_type: str
    source_id: str
    title: str
    detail_path: str

    @classmethod
    def from_entity(
        cls, source_ref: MemoryCompactSourceRef
    ) -> MemoryCompactSourceRefResponse:
        """Create response from domain entity.

        Args:
            source_ref: Domain source-reference entity.

        Returns:
            Public source-reference response schema.
        """
        return cls(
            id=source_ref.id,
            compact_id=source_ref.compact_id,
            source_type=source_ref.source_type,
            source_id=source_ref.source_id,
            title=source_ref.title,
            detail_path=source_ref.detail_path,
        )


class MemoryCompactResponse(StrictSchemaModel):
    """Response schema for one Memory Compact."""

    id: str
    project: str | None
    covered_from: AwareTimestamp
    covered_to: AwareTimestamp
    markdown_body: str
    status: MemoryCompactStatus
    source_refs: list[MemoryCompactSourceRefResponse]
    created_at: AwareTimestamp
    updated_at: AwareTimestamp
    archived_at: AwareTimestamp | None

    @classmethod
    def from_entity(cls, compact: MemoryCompact) -> MemoryCompactResponse:
        """Create response from domain entity.

        Args:
            compact: Domain Memory Compact entity.

        Returns:
            Public Memory Compact response schema.
        """
        return cls(
            id=compact.id,
            project=compact.project,
            covered_from=compact.covered_from,
            covered_to=compact.covered_to,
            markdown_body=compact.markdown_body,
            status=compact.status,
            source_refs=[
                MemoryCompactSourceRefResponse.from_entity(source_ref)
                for source_ref in compact.source_refs
            ],
            created_at=compact.created_at,
            updated_at=compact.updated_at,
            archived_at=compact.archived_at,
        )


class MemoryCompactListResponse(StrictSchemaModel):
    """Paginated Memory Compact response."""

    items: list[MemoryCompactResponse]
    total: int
