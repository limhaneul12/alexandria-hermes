"""Strict reconciliation-aware Memory Compact response schemas."""

from __future__ import annotations

from app.memory.domain.entities.memory_reconciliation import (
    MemoryCompactFact,
    MemoryCompactFactBuckets,
    MemoryCompactSafetyReview,
)
from app.memory.domain.event_enum.reconciliation_enums import (
    MemoryCompactFactCategory,
    MemoryCompactSafetyIssue,
)
from app.shared.schemas.common_schemas import StrictSchemaModel
from app.shared.schemas.datetime_schemas import AwareTimestamp


class MemoryCompactFactResponse(StrictSchemaModel):
    """One temporally classified fact prepared for safe compaction."""

    context_id: str
    title: str
    content: str
    category: MemoryCompactFactCategory
    valid_from: AwareTimestamp | None
    valid_to: AwareTimestamp | None
    evidence_refs: list[str]
    conflict_set_ids: list[str]
    relation_summary: list[str]

    @classmethod
    def from_entity(cls, value: MemoryCompactFact) -> MemoryCompactFactResponse:
        """Convert one internal fact into a strict HTTP response.

        Args:
            value: Value.

        Returns:
            MemoryCompactFactResponse: Operation result.
        """
        return cls(
            context_id=value.context_id,
            title=value.title,
            content=value.content,
            category=value.category,
            valid_from=value.valid_from,
            valid_to=value.valid_to,
            evidence_refs=list(value.evidence_refs),
            conflict_set_ids=list(value.conflict_set_ids),
            relation_summary=list(value.relation_summary),
        )


class MemoryCompactFactBucketsResponse(StrictSchemaModel):
    """Fact sections that must remain separate during Memory Compact generation."""

    current_facts: list[MemoryCompactFactResponse]
    historical_facts: list[MemoryCompactFactResponse]
    open_conflicts: list[MemoryCompactFactResponse]
    uncertain_claims: list[MemoryCompactFactResponse]
    superseded_facts: list[MemoryCompactFactResponse]

    @classmethod
    def from_entity(
        cls,
        value: MemoryCompactFactBuckets,
    ) -> MemoryCompactFactBucketsResponse:
        """Convert all reconciliation-aware fact buckets into HTTP responses.

        Args:
            value: Value.

        Returns:
            MemoryCompactFactBucketsResponse: Operation result.
        """
        return cls(
            current_facts=[
                MemoryCompactFactResponse.from_entity(item)
                for item in value.current_facts
            ],
            historical_facts=[
                MemoryCompactFactResponse.from_entity(item)
                for item in value.historical_facts
            ],
            open_conflicts=[
                MemoryCompactFactResponse.from_entity(item)
                for item in value.open_conflicts
            ],
            uncertain_claims=[
                MemoryCompactFactResponse.from_entity(item)
                for item in value.uncertain_claims
            ],
            superseded_facts=[
                MemoryCompactFactResponse.from_entity(item)
                for item in value.superseded_facts
            ],
        )


class MemoryCompactSafetyReviewResponse(StrictSchemaModel):
    """Safe pre-publication review for reconciliation-aware Memory Compact input."""

    buckets: MemoryCompactFactBucketsResponse
    issues: list[MemoryCompactSafetyIssue]
    safe_to_publish: bool
    warnings: list[str]
    rendered_markdown: str

    @classmethod
    def from_entity(
        cls,
        value: MemoryCompactSafetyReview,
    ) -> MemoryCompactSafetyReviewResponse:
        """Convert one Compact safety review into a strict HTTP response.

        Args:
            value: Value.

        Returns:
            MemoryCompactSafetyReviewResponse: Operation result.
        """
        return cls(
            buckets=MemoryCompactFactBucketsResponse.from_entity(value.buckets),
            issues=list(value.issues),
            safe_to_publish=value.safe_to_publish,
            warnings=list(value.warnings),
            rendered_markdown=value.rendered_markdown,
        )
