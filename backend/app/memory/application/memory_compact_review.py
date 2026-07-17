"""Deterministic Memory Compact librarian review rubric."""

from __future__ import annotations

import re
from dataclasses import dataclass

from app.memory.domain.entities.memory_compact import (
    MemoryCompact,
    MemoryCompactSourceRef,
)
from app.memory.domain.event_enum.memory_compact_enums import (
    MemoryCompactReviewVerdict,
)


@dataclass(frozen=True, slots=True, kw_only=True)
class MemoryCompactSourceObservation:
    """Observed current evidence state for one compact source ref."""

    source_id: str
    detail_path: str | None = None
    current_source_hash: str | None = None


@dataclass(frozen=True, slots=True, kw_only=True)
class MemoryCompactRubricScore:
    """Single rubric item score for a Memory Compact review."""

    code: str
    label: str
    score: int
    required: bool
    reasons: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True, kw_only=True)
class MemoryCompactReviewResult:
    """Structured librarian review result for a Memory Compact."""

    compact_id: str
    verdict: MemoryCompactReviewVerdict
    total_score: int
    max_score: int
    scores: tuple[MemoryCompactRubricScore, ...]
    missing_refs: tuple[str, ...] = ()
    contradictions: tuple[str, ...] = ()
    stale_reasons: tuple[str, ...] = ()
    recommended_actions: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class _RubricSpec:
    code: str
    label: str
    required: bool


_RUBRIC: tuple[_RubricSpec, ...] = (
    _RubricSpec("durable_decisions", "Durable Decisions", True),
    _RubricSpec("current_state", "Current State", True),
    _RubricSpec("risks_blockers", "Risks and Blockers", True),
    _RubricSpec("next_actions", "Next Actions", True),
    _RubricSpec("evidence_completeness", "Evidence Completeness", True),
    _RubricSpec("project_isolation", "Project Isolation", True),
    _RubricSpec("freshness", "Freshness", True),
    _RubricSpec("concision", "Concision", False),
    _RubricSpec("contradiction_handling", "Contradiction Handling", True),
    _RubricSpec("actionability", "Actionability", False),
)
_REQUIRED_TWO_SCORE_CODES = frozenset(
    {"evidence_completeness", "current_state", "project_isolation"}
)
_BLOCKING_CONTRADICTION_PATTERNS = (
    "unresolved contradiction",
    "blocking contradiction",
    "contradiction unresolved",
    "미해결 모순",
    "차단급 모순",
)


def review_memory_compact(
    compact: MemoryCompact,
    *,
    source_observations: tuple[MemoryCompactSourceObservation, ...] = (),
) -> MemoryCompactReviewResult:
    """Review a compact using the PRD-required librarian rubric.

    Args:
        compact: Compact under review.
        source_observations: Optional current source-hash evidence.

    Returns:
        Structured review verdict, rubric scores, and recommended actions.
    """
    sections = _markdown_sections(compact.markdown_body)
    missing_refs = _missing_ref_reasons(compact.source_refs)
    stale_reasons = _stale_reasons(compact.source_refs, source_observations)
    contradictions = _contradictions(compact.markdown_body)
    scores = tuple(
        _score_rubric_item(
            spec=spec,
            compact=compact,
            sections=sections,
            missing_refs=missing_refs,
            stale_reasons=stale_reasons,
            contradictions=contradictions,
        )
        for spec in _RUBRIC
    )
    total_score = sum(score.score for score in scores)
    score_by_code = {score.code: score.score for score in scores}
    blocking_reasons = bool(missing_refs or stale_reasons or contradictions)
    required_zero = any(score.required and score.score == 0 for score in scores)
    required_two_missing = any(
        score_by_code[code] < 2 for code in _REQUIRED_TWO_SCORE_CODES
    )
    if blocking_reasons:
        verdict = MemoryCompactReviewVerdict.BLOCKED
    elif required_zero or required_two_missing or total_score < 17:
        verdict = MemoryCompactReviewVerdict.NEEDS_REVISION
    else:
        verdict = MemoryCompactReviewVerdict.PASS
    return MemoryCompactReviewResult(
        compact_id=compact.id,
        verdict=verdict,
        total_score=total_score,
        max_score=len(_RUBRIC) * 2,
        scores=scores,
        missing_refs=missing_refs,
        contradictions=contradictions,
        stale_reasons=stale_reasons,
        recommended_actions=_recommended_actions(
            verdict=verdict,
            scores=scores,
            missing_refs=missing_refs,
            stale_reasons=stale_reasons,
            contradictions=contradictions,
        ),
    )


def _score_rubric_item(
    *,
    spec: _RubricSpec,
    compact: MemoryCompact,
    sections: dict[str, str],
    missing_refs: tuple[str, ...],
    stale_reasons: tuple[str, ...],
    contradictions: tuple[str, ...],
) -> MemoryCompactRubricScore:
    if spec.code == "evidence_completeness":
        score, reasons = _score_evidence_completeness(
            sections=sections,
            source_refs=compact.source_refs,
            missing_refs=missing_refs,
        )
    elif spec.code == "project_isolation":
        score, reasons = _score_project_isolation(compact, sections)
    elif spec.code == "freshness":
        score = 0 if stale_reasons else 2
        reasons = stale_reasons
    elif spec.code == "concision":
        score, reasons = _score_concision(compact.markdown_body)
    elif spec.code == "contradiction_handling":
        score = 0 if contradictions else 2
        reasons = contradictions
    elif spec.code == "actionability":
        score, reasons = _score_actionability(sections)
    else:
        score, reasons = _score_required_section(spec.code, sections)
    return MemoryCompactRubricScore(
        code=spec.code,
        label=spec.label,
        score=score,
        required=spec.required,
        reasons=reasons,
    )


def _score_required_section(
    code: str,
    sections: dict[str, str],
) -> tuple[int, tuple[str, ...]]:
    section = sections.get(code, "").strip()
    if not section:
        return 0, (f"{code}_missing",)
    if len(_words(section)) < 3:
        return 1, (f"{code}_too_thin",)
    return 2, ()


def _score_project_isolation(
    compact: MemoryCompact,
    sections: dict[str, str],
) -> tuple[int, tuple[str, ...]]:
    if compact.project is None:
        return 2, ()
    body = "\n".join(sections.values()).lower()
    project = compact.project.lower()
    project_lines = [
        line.strip().lower()
        for line in body.splitlines()
        if line.strip().startswith("- project:") or line.strip().startswith("project:")
    ]
    if any(project not in line for line in project_lines):
        return 0, ("project_scope_mismatch",)
    if project in body:
        return 2, ()
    return 1, ("project_scope_not_explicit",)


def _score_concision(markdown_body: str) -> tuple[int, tuple[str, ...]]:
    if len(markdown_body) > 12_000:
        return 0, ("compact_too_long",)
    if len(markdown_body) > 8_000:
        return 1, ("compact_verbose",)
    return 2, ()


def _score_actionability(sections: dict[str, str]) -> tuple[int, tuple[str, ...]]:
    next_actions = sections.get("next_actions", "")
    if not next_actions.strip():
        return 0, ("next_actions_missing",)
    if len(_words(next_actions)) < 3:
        return 1, ("next_actions_too_thin",)
    return 2, ()


def _score_evidence_completeness(
    *,
    sections: dict[str, str],
    source_refs: tuple[MemoryCompactSourceRef, ...],
    missing_refs: tuple[str, ...],
) -> tuple[int, tuple[str, ...]]:
    if missing_refs:
        return 0, missing_refs
    evidence_summary = sections.get("evidence_summary", "")
    unlinked = _unlinked_source_refs(evidence_summary, source_refs)
    if unlinked:
        return 1, unlinked
    return 2, ()


def _missing_ref_reasons(
    source_refs: tuple[MemoryCompactSourceRef, ...],
) -> tuple[str, ...]:
    if not source_refs:
        return ("source_refs_missing",)
    reasons: list[str] = []
    for source_ref in source_refs:
        if (
            not source_ref.source_type.strip()
            or not source_ref.source_id.strip()
            or not source_ref.title.strip()
            or not source_ref.detail_path.strip()
        ):
            reasons.append(f"source_ref_incomplete:{source_ref.source_id or 'unknown'}")
        if source_ref.detail_path.strip().lower().startswith(("missing:", "broken:")):
            reasons.append(f"source_ref_broken:{source_ref.source_id}")
    return tuple(reasons)


def _unlinked_source_refs(
    evidence_summary: str,
    source_refs: tuple[MemoryCompactSourceRef, ...],
) -> tuple[str, ...]:
    normalized_summary = evidence_summary.lower()
    reasons: list[str] = []
    for source_ref in source_refs:
        markers = (
            source_ref.source_id.strip().lower(),
            source_ref.detail_path.strip().lower(),
            source_ref.title.strip().lower(),
        )
        if not any(marker and marker in normalized_summary for marker in markers):
            reasons.append(f"source_ref_unlinked:{source_ref.source_id}")
    return tuple(reasons)


def _stale_reasons(
    source_refs: tuple[MemoryCompactSourceRef, ...],
    source_observations: tuple[MemoryCompactSourceObservation, ...],
) -> tuple[str, ...]:
    observations = {
        _observation_key(observation): observation
        for observation in source_observations
        if observation.current_source_hash is not None
    }
    reasons: list[str] = []
    for source_ref in source_refs:
        observation = observations.get(_source_ref_key(source_ref))
        if observation is None:
            observation = observations.get((source_ref.source_id, None))
        if (
            observation is not None
            and source_ref.source_hash is not None
            and observation.current_source_hash != source_ref.source_hash
        ):
            reasons.append(f"source_hash_mismatch:{source_ref.source_id}")
    return tuple(reasons)


def _contradictions(markdown_body: str) -> tuple[str, ...]:
    body = markdown_body.lower()
    return tuple(
        pattern.replace(" ", "_")
        for pattern in _BLOCKING_CONTRADICTION_PATTERNS
        if pattern in body
    )


def _recommended_actions(
    *,
    verdict: MemoryCompactReviewVerdict,
    scores: tuple[MemoryCompactRubricScore, ...],
    missing_refs: tuple[str, ...],
    stale_reasons: tuple[str, ...],
    contradictions: tuple[str, ...],
) -> tuple[str, ...]:
    actions: list[str] = []
    if missing_refs:
        actions.append("repair_source_refs")
    if stale_reasons:
        actions.append("refresh_source_evidence")
    if contradictions:
        actions.append("resolve_contradictions")
    evidence_score = next(
        score for score in scores if score.code == "evidence_completeness"
    )
    if evidence_score.score < 2 and not missing_refs:
        actions.append("improve_evidence_completeness")
    low_score_codes = [
        score.code
        for score in scores
        if score.required
        and score.score == 0
        and score.code
        not in {"evidence_completeness", "freshness", "contradiction_handling"}
    ]
    if low_score_codes:
        actions.append("revise_required_sections:" + ",".join(low_score_codes))
    if verdict is MemoryCompactReviewVerdict.PASS:
        actions.append("promote_or_keep_current")
    elif not actions:
        actions.append("revise_memory_compact")
    return tuple(actions)


def _markdown_sections(markdown_body: str) -> dict[str, str]:
    sections: dict[str, list[str]] = {}
    current_key: str | None = None
    for line in markdown_body.splitlines():
        match = re.match(r"^#{1,6}\s+(.+?)\s*$", line)
        if match:
            current_key = _section_key(match.group(1))
            sections.setdefault(current_key, [])
            continue
        if current_key is not None:
            sections[current_key].append(line)
    return {key: "\n".join(lines).strip() for key, lines in sections.items()}


def _section_key(heading: str) -> str:
    normalized = re.sub(r"[^a-z0-9]+", " ", heading.lower()).strip()
    if normalized == "durable decisions":
        return "durable_decisions"
    if normalized == "current state":
        return "current_state"
    if normalized in {"risks and blockers", "risks blockers"}:
        return "risks_blockers"
    if normalized == "next actions":
        return "next_actions"
    if normalized == "evidence summary":
        return "evidence_summary"
    return normalized.replace(" ", "_")


def _words(value: str) -> list[str]:
    return re.findall(r"[\w가-힣]+", value)


def _source_ref_key(source_ref: MemoryCompactSourceRef) -> tuple[str, str | None]:
    return source_ref.source_id, source_ref.detail_path


def _observation_key(
    observation: MemoryCompactSourceObservation,
) -> tuple[str, str | None]:
    return observation.source_id, observation.detail_path
