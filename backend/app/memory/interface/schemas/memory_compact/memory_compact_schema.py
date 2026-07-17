"""Schemas for Memory Compact HTTP boundaries."""

from __future__ import annotations

from typing import Annotated

from app.memory.application.memory_compact_review import (
    MemoryCompactReviewResult,
    MemoryCompactRubricScore,
    MemoryCompactSourceObservation,
)
from app.memory.domain.entities.memory_compact import (
    MemoryCompact,
    MemoryCompactSourceRef,
)
from app.memory.domain.event_enum.memory_compact_enums import (
    MemoryCompactReviewVerdict,
    MemoryCompactStatus,
)
from app.memory.domain.repositories.memory_compact_repository import (
    MemoryCompactCreate,
    MemoryCompactSourceRefCreate,
)
from app.shared.schemas.common_schemas import StrictSchemaModel
from app.shared.schemas.datetime_schemas import AwareTimestamp
from app.shared.types.extra_types import JSONObject
from pydantic import Field, StringConstraints

NonBlankString = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


class MemoryCompactSourceRefRequest(StrictSchemaModel):
    """Request schema for a compact source reference."""

    source_type: NonBlankString
    source_id: NonBlankString
    title: NonBlankString
    detail_path: NonBlankString
    source_hash: str | None = None

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
            source_hash=self.source_hash,
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
    source_hash: str | None

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
            source_hash=source_ref.source_hash,
        )


class MemoryCompactRagGateResponse(StrictSchemaModel):
    """RAG healthy-gate result attached to CURRENT create/promote responses."""

    gate_status: str
    checked_at: AwareTimestamp
    fingerprint: JSONObject | None
    warnings: list[str] = Field(default_factory=list)


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
    review_verdict: MemoryCompactReviewVerdict | None
    review_score: int | None
    review_max_score: int | None
    reviewed_at: AwareTimestamp | None
    warnings: list[str] = Field(default_factory=list)
    deduplicated: bool = False
    rag_gate: MemoryCompactRagGateResponse | None = None

    @classmethod
    def from_entity(
        cls,
        compact: MemoryCompact,
        *,
        warnings: list[str] | None = None,
        rag_gate: MemoryCompactRagGateResponse | None = None,
    ) -> MemoryCompactResponse:
        """Create response from domain entity.

        Args:
            compact: Domain Memory Compact entity.
            warnings: Additional response-only warning codes.
            rag_gate: Optional RAG gate result for create/promote calls.

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
            review_verdict=compact.review_verdict,
            review_score=compact.review_score,
            review_max_score=compact.review_max_score,
            reviewed_at=compact.reviewed_at,
            warnings=_response_warnings(
                [*compact.metadata_warnings, *(warnings or [])]
            ),
            deduplicated=compact.deduplicated,
            rag_gate=rag_gate,
        )


class MemoryCompactListResponse(StrictSchemaModel):
    """Paginated Memory Compact response."""

    items: list[MemoryCompactResponse]
    total: int


def _response_warnings(warnings: list[str]) -> list[str]:
    normalized: list[str] = []
    seen: set[str] = set()
    for warning in warnings:
        value = _current_warning_code(warning)
        if value in seen:
            continue
        seen.add(value)
        normalized.append(value)
    return normalized


def _current_warning_code(warning: str) -> str:
    if warning == "memory_compact_stale":
        return "current_memory_compact_stale"
    if warning == "memory_compact_timestamp_missing":
        return "current_memory_compact_timestamp_missing"
    return warning


class MemoryCompactSourceObservationRequest(StrictSchemaModel):
    """Observed current source state for review-time freshness checks."""

    source_id: str = Field(min_length=1)
    detail_path: str | None = None
    current_source_hash: str | None = None

    def to_observation(self) -> MemoryCompactSourceObservation:
        """Convert request schema to application review input.

        Returns:
            Source observation dataclass.
        """
        return MemoryCompactSourceObservation(
            source_id=self.source_id,
            detail_path=self.detail_path,
            current_source_hash=self.current_source_hash,
        )


class MemoryCompactReviewRequest(StrictSchemaModel):
    """Request schema for librarian review of a Memory Compact."""

    source_observations: list[MemoryCompactSourceObservationRequest] = Field(
        default_factory=list
    )

    def to_observations(self) -> tuple[MemoryCompactSourceObservation, ...]:
        """Convert request schema to application review observations.

        Returns:
            Source observations tuple.
        """
        return tuple(
            observation.to_observation() for observation in self.source_observations
        )


class MemoryCompactRubricScoreResponse(StrictSchemaModel):
    """Response schema for a single rubric score."""

    code: str
    label: str
    score: int
    required: bool
    reasons: list[str]

    @classmethod
    def from_result(
        cls, score: MemoryCompactRubricScore
    ) -> MemoryCompactRubricScoreResponse:
        """Create response schema from rubric score.

        Args:
            score: Internal rubric score dataclass.

        Returns:
            Public rubric score response.
        """
        return cls(
            code=score.code,
            label=score.label,
            score=score.score,
            required=score.required,
            reasons=list(score.reasons),
        )


class MemoryCompactReviewResponse(StrictSchemaModel):
    """Response schema for librarian Memory Compact review."""

    compact_id: str
    verdict: MemoryCompactReviewVerdict
    total_score: int
    max_score: int
    scores: list[MemoryCompactRubricScoreResponse]
    missing_refs: list[str]
    contradictions: list[str]
    stale_reasons: list[str]
    recommended_actions: list[str]

    @classmethod
    def from_result(
        cls, result: MemoryCompactReviewResult
    ) -> MemoryCompactReviewResponse:
        """Create response schema from review result.

        Args:
            result: Application review result.

        Returns:
            Public review response.
        """
        return cls(
            compact_id=result.compact_id,
            verdict=result.verdict,
            total_score=result.total_score,
            max_score=result.max_score,
            scores=[
                MemoryCompactRubricScoreResponse.from_result(score)
                for score in result.scores
            ],
            missing_refs=list(result.missing_refs),
            contradictions=list(result.contradictions),
            stale_reasons=list(result.stale_reasons),
            recommended_actions=list(result.recommended_actions),
        )
