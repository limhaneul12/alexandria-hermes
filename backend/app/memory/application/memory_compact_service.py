"""Application service for Memory Compact lifecycle."""

from __future__ import annotations

import re
from dataclasses import dataclass, replace
from datetime import UTC, datetime
from hashlib import sha256

from app.memory.application.memory_compact_review import (
    MemoryCompactReviewResult,
    MemoryCompactSourceObservation,
    review_memory_compact,
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
    IMemoryCompactRepository,
    MemoryCompactCreate,
    MemoryCompactSourceRefCreate,
)
from app.shared.exceptions import (
    MemoryCompactNotFoundError,
    MemoryCompactValidationError,
)
from app.shared.types.types_convert_utils import aware_utc_datetime, enum_value

_CURRENT_REQUIRED_SECTIONS: tuple[tuple[str, str], ...] = (
    ("durable decisions", "Durable Decisions"),
    ("current state", "Current State"),
    ("risks and blockers", "Risks and Blockers"),
    ("next actions", "Next Actions"),
    ("coverage", "Coverage"),
    ("evidence summary", "Evidence Summary"),
)


@dataclass(frozen=True, slots=True)
class _SourceRefSignature:
    """Stable source-ref key used for duplicate Memory Compact detection."""

    source_type: str
    source_id: str
    detail_path: str
    source_hash: str | None


@dataclass(frozen=True, slots=True)
class _MemoryCompactSignature:
    """Stable signature for a Memory Compact candidate."""

    project: str | None
    covered_from: datetime
    covered_to: datetime
    source_refs: tuple[_SourceRefSignature, ...]
    body_hash: str


class MemoryCompactService:
    """Coordinate first-class durable Memory Compact artifacts."""

    def __init__(self, repository: IMemoryCompactRepository) -> None:
        """Initialize service dependencies.

        Args:
            repository: Persistence port for Memory Compact artifacts.
        """
        self._repository = repository

    async def create(self, payload: MemoryCompactCreate) -> MemoryCompact:
        """Create a compact and enforce lifecycle invariants.

        Args:
            payload: Validated Memory Compact creation contract.

        Returns:
            Created Memory Compact entity.
        """
        payload = MemoryCompactCreate(
            project=payload.project,
            covered_from=payload.covered_from,
            covered_to=payload.covered_to,
            markdown_body=payload.markdown_body,
            status=enum_value(payload.status, MemoryCompactStatus, "status"),
            source_refs=_deduplicate_source_refs(payload.source_refs),
            review_verdict=payload.review_verdict,
            review_score=payload.review_score,
            review_max_score=payload.review_max_score,
            reviewed_at=payload.reviewed_at,
        )
        self._validate_create(payload)
        if payload.status is MemoryCompactStatus.CURRENT:
            review = review_memory_compact(_candidate_compact(payload))
            _ensure_review_passes(review)
            payload = _with_review_metadata(payload, review)
        existing = await self._find_existing_by_signature(payload)
        if existing is not None:
            return replace(existing, deduplicated=True)
        return await self._repository.create(payload)

    async def get(self, compact_id: str) -> MemoryCompact:
        """Read one Memory Compact by id.

        Args:
            compact_id: Memory Compact identifier.

        Returns:
            Matching Memory Compact entity.
        """
        compact = await self._repository.get(compact_id)
        if compact is None:
            raise MemoryCompactNotFoundError(f"Memory compact not found: {compact_id}")
        return compact

    async def list_compacts(
        self,
        *,
        project: str | None = None,
        status: MemoryCompactStatus | None = None,
        covered_after: datetime | None = None,
        covered_before: datetime | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[MemoryCompact], int]:
        """List Memory Compacts.

        Args:
            project: Project filter.
            status: Lifecycle status filter.
            covered_after: Coverage-overlap lower bound.
            covered_before: Coverage-overlap upper bound.
            limit: Maximum number of rows to return.
            offset: Number of rows to skip.

        Returns:
            Page of Memory Compacts and the total matching count.
        """
        if status is not None:
            status = enum_value(status, MemoryCompactStatus, "status")
        bounded_limit = min(max(int(limit), 1), 200)
        bounded_offset = max(int(offset), 0)
        return await self._repository.list_compacts(
            project=project,
            status=status,
            covered_after=covered_after,
            covered_before=covered_before,
            limit=bounded_limit,
            offset=bounded_offset,
        )

    async def current(self, *, project: str | None = None) -> MemoryCompact:
        """Read the current compact for a project.

        Args:
            project: Optional project filter; None addresses the default project.

        Returns:
            Current Memory Compact entity.
        """
        compact = await self._repository.current(project=project)
        if compact is None:
            label = "default project" if project is None else project
            raise MemoryCompactNotFoundError(
                f"Current memory compact not found: {label}"
            )
        return compact

    async def mark_current(self, compact_id: str) -> MemoryCompact:
        """Mark one compact as current.

        Args:
            compact_id: Memory Compact identifier.

        Returns:
            Updated current Memory Compact entity.
        """
        compact = await self.get(compact_id)
        if not compact.source_refs:
            raise MemoryCompactValidationError(
                "Current memory compact requires source refs"
            )
        missing_sections = _missing_current_sections(compact.markdown_body)
        if missing_sections:
            raise MemoryCompactValidationError(
                "Current memory compact missing required sections: "
                + ", ".join(missing_sections)
            )
        review = review_memory_compact(compact)
        _ensure_review_passes(review)
        return await self._repository.mark_current(
            compact_id,
            review_verdict=review.verdict,
            review_score=review.total_score,
            review_max_score=review.max_score,
            reviewed_at=datetime.now(UTC),
        )

    async def archive(self, compact_id: str) -> MemoryCompact:
        """Archive one Memory Compact.

        Args:
            compact_id: Memory Compact identifier.

        Returns:
            Archived Memory Compact entity.
        """
        return await self._repository.archive(compact_id)

    async def delete(self, compact_id: str) -> None:
        """Hard delete one Memory Compact.

        Args:
            compact_id: Memory Compact identifier.

        Returns:
            None.
        """
        await self._repository.delete(compact_id)

    async def review(
        self,
        compact_id: str,
        *,
        source_observations: tuple[MemoryCompactSourceObservation, ...] = (),
    ) -> MemoryCompactReviewResult:
        """Review one Memory Compact against the librarian rubric.

        Args:
            compact_id: Memory Compact identifier.
            source_observations: Optional current source evidence observations.

        Returns:
            Structured review result.
        """
        compact = await self.get(compact_id)
        return review_memory_compact(
            compact,
            source_observations=source_observations,
        )

    def _validate_create(self, payload: MemoryCompactCreate) -> None:
        if payload.covered_to < payload.covered_from:
            raise MemoryCompactValidationError("covered_to must be after covered_from")
        if not payload.markdown_body.strip():
            raise MemoryCompactValidationError("markdown_body is required")
        if payload.status is MemoryCompactStatus.CURRENT and not payload.source_refs:
            raise MemoryCompactValidationError(
                "Current memory compact requires source refs"
            )
        if payload.status is MemoryCompactStatus.CURRENT:
            missing_sections = _missing_current_sections(payload.markdown_body)
            if missing_sections:
                raise MemoryCompactValidationError(
                    "Current memory compact missing required sections: "
                    + ", ".join(missing_sections)
                )
        for source_ref in payload.source_refs:
            if (
                not source_ref.source_type.strip()
                or not source_ref.source_id.strip()
                or not source_ref.title.strip()
                or not source_ref.detail_path.strip()
            ):
                raise MemoryCompactValidationError(
                    "Memory compact source ref fields are required"
                )

    async def _find_existing_by_signature(
        self,
        payload: MemoryCompactCreate,
    ) -> MemoryCompact | None:
        signature = _create_signature(payload)
        offset = 0
        while True:
            compacts, total = await self._repository.list_compacts(
                project=payload.project,
                limit=200,
                offset=offset,
            )
            for compact in compacts:
                if _compact_signature(compact) == signature:
                    return compact
            if not compacts or offset + len(compacts) >= total:
                return None
            offset += len(compacts)


def _deduplicate_source_refs(
    source_refs: list[MemoryCompactSourceRefCreate],
) -> list[MemoryCompactSourceRefCreate]:
    deduplicated: list[MemoryCompactSourceRefCreate] = []
    seen: set[tuple[str, str, str]] = set()
    for source_ref in source_refs:
        key = (source_ref.source_type, source_ref.source_id, source_ref.detail_path)
        if key in seen:
            continue
        seen.add(key)
        deduplicated.append(source_ref)
    return deduplicated


def _missing_current_sections(markdown_body: str) -> list[str]:
    headings = {
        _normalize_section_heading(match.group(1))
        for match in re.finditer(r"^#{1,6}\s+(.+?)\s*$", markdown_body, re.MULTILINE)
    }
    return [
        display
        for normalized, display in _CURRENT_REQUIRED_SECTIONS
        if normalized not in headings
    ]


def _normalize_section_heading(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", value.lower()).strip()


def _create_signature(payload: MemoryCompactCreate) -> _MemoryCompactSignature:
    return _MemoryCompactSignature(
        project=payload.project,
        covered_from=aware_utc_datetime(payload.covered_from),
        covered_to=aware_utc_datetime(payload.covered_to),
        source_refs=tuple(
            sorted(
                (
                    _SourceRefSignature(
                        source_type=source_ref.source_type,
                        source_id=source_ref.source_id,
                        detail_path=source_ref.detail_path,
                        source_hash=source_ref.source_hash,
                    )
                    for source_ref in payload.source_refs
                ),
                key=_source_ref_signature_sort_key,
            )
        ),
        body_hash=_body_hash(payload.markdown_body),
    )


def _compact_signature(compact: MemoryCompact) -> _MemoryCompactSignature:
    return _MemoryCompactSignature(
        project=compact.project,
        covered_from=aware_utc_datetime(compact.covered_from),
        covered_to=aware_utc_datetime(compact.covered_to),
        source_refs=tuple(
            sorted(
                (
                    _SourceRefSignature(
                        source_type=source_ref.source_type,
                        source_id=source_ref.source_id,
                        detail_path=source_ref.detail_path,
                        source_hash=source_ref.source_hash,
                    )
                    for source_ref in compact.source_refs
                ),
                key=_source_ref_signature_sort_key,
            )
        ),
        body_hash=_body_hash(compact.markdown_body),
    )


def _source_ref_signature_sort_key(
    source_ref: _SourceRefSignature,
) -> tuple[str, str, str, str]:
    return (
        source_ref.source_type,
        source_ref.source_id,
        source_ref.detail_path,
        source_ref.source_hash or "",
    )


def _body_hash(markdown_body: str) -> str:
    return sha256(markdown_body.strip().encode("utf-8")).hexdigest()


def _candidate_compact(payload: MemoryCompactCreate) -> MemoryCompact:
    covered_from = aware_utc_datetime(payload.covered_from)
    covered_to = aware_utc_datetime(payload.covered_to)
    return MemoryCompact(
        id="__candidate__",
        project=payload.project,
        covered_from=covered_from,
        covered_to=covered_to,
        markdown_body=payload.markdown_body,
        status=payload.status,
        source_refs=tuple(
            MemoryCompactSourceRef(
                id=f"__candidate_source_{index}__",
                compact_id="__candidate__",
                source_type=source_ref.source_type,
                source_id=source_ref.source_id,
                title=source_ref.title,
                detail_path=source_ref.detail_path,
                source_hash=source_ref.source_hash,
            )
            for index, source_ref in enumerate(payload.source_refs)
        ),
        created_at=covered_to,
        updated_at=covered_to,
        archived_at=None,
        review_verdict=payload.review_verdict,
        review_score=payload.review_score,
        review_max_score=payload.review_max_score,
        reviewed_at=payload.reviewed_at,
    )


def _with_review_metadata(
    payload: MemoryCompactCreate,
    review: MemoryCompactReviewResult,
) -> MemoryCompactCreate:
    return MemoryCompactCreate(
        project=payload.project,
        covered_from=payload.covered_from,
        covered_to=payload.covered_to,
        markdown_body=payload.markdown_body,
        status=payload.status,
        source_refs=payload.source_refs,
        review_verdict=review.verdict,
        review_score=review.total_score,
        review_max_score=review.max_score,
        reviewed_at=datetime.now(UTC),
    )


def _ensure_review_passes(review: MemoryCompactReviewResult) -> None:
    if review.verdict is MemoryCompactReviewVerdict.PASS:
        return
    reasons = [*review.missing_refs, *review.contradictions, *review.stale_reasons]
    if not reasons:
        reasons = list(review.recommended_actions)
    reason_text = ",".join(reasons) if reasons else "rubric_not_passed"
    raise MemoryCompactValidationError(
        f"Current memory compact review failed: {review.verdict.value}: {reason_text}"
    )
