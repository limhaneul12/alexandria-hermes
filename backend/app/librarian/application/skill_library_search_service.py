"""Search-first evaluator for reusable skill-library artifacts."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Protocol

from app.librarian.domain.event_enum.skill_acquisition_enums import RiskLevel
from app.obsidian.domain.contracts.obsidian_contracts import ObsidianSearchQuery
from app.obsidian.domain.entities.obsidian_note import ObsidianSearchHit
from app.obsidian.domain.event_enum.obsidian_enums import AlexandriaNoteType
from app.shared.types.extra_types import JSONObject, JSONValue


class SkillSearchDecision(StrEnum):
    """Search-first decision before creating an acquisition job."""

    FOUND_SUFFICIENT = "FOUND_SUFFICIENT"
    FOUND_PARTIAL = "FOUND_PARTIAL"
    NOT_FOUND = "NOT_FOUND"
    SEARCH_UNAVAILABLE = "SEARCH_UNAVAILABLE"


@dataclass(frozen=True, slots=True, kw_only=True)
class SkillCapabilityBrief:
    """Normalized capability need used for skill-library search."""

    capability: str
    task_goal: str | None = None
    project: str | None = None
    environment: str | None = None
    required_tools: list[str] = field(default_factory=list)
    constraints: list[str] = field(default_factory=list)
    risk_tolerance: RiskLevel = RiskLevel.MEDIUM
    success_criteria: list[str] = field(default_factory=list)
    limit: int = 5


@dataclass(frozen=True, slots=True, kw_only=True)
class SkillSearchCandidate:
    """One normalized reusable skill candidate."""

    id: str
    path: str
    title: str
    status: str
    version: str | None
    project: str | None
    required_tools: list[str]
    risk_level: RiskLevel
    evidence: list[str]
    matched_terms: list[str]
    limitations: list[str]
    score: float
    sufficiency_score: int
    hard_gates: JSONObject
    why_match: list[str]
    gaps: list[str]
    recommended_action: str


@dataclass(frozen=True, slots=True, kw_only=True)
class SkillSearchResult:
    """Search-first result for one normalized capability brief."""

    decision: SkillSearchDecision
    query: str
    candidates: list[SkillSearchCandidate]
    recommended_action: str
    gaps: list[str]
    decision_explanation: JSONObject = field(default_factory=dict)
    handoff: JSONObject | None = None
    search_error: str | None = None


class SkillSearchBackend(Protocol):
    """Minimal Obsidian search capability required by the evaluator."""

    async def search(
        self,
        query: ObsidianSearchQuery,
        *,
        refresh: bool = True,
    ) -> list[ObsidianSearchHit]:
        """Return matching Obsidian search hits.

        Args:
            query: Obsidian search query.
            refresh: Whether to refresh the index before searching.

        Returns:
            Ranked Obsidian search hits.
        """


class SkillLibrarySearchService:
    """Evaluate existing skill-library notes before librarian escalation."""

    def __init__(self, search_backend: SkillSearchBackend) -> None:
        """Create evaluator.

        Args:
            search_backend: Obsidian search boundary.
        """
        self._search_backend = search_backend

    async def search_first(self, brief: SkillCapabilityBrief) -> SkillSearchResult:
        """Search reusable skills and classify sufficiency.

        Args:
            brief: Normalized capability need.

        Returns:
            Decision payload; search failures are explicit and never converted to
            empty results.
        """
        query_text = _query_text(brief)
        try:
            hits = await self._search_backend.search(
                ObsidianSearchQuery(
                    query=query_text,
                    limit=max(1, min(brief.limit, 10)),
                    alexandria_type=AlexandriaNoteType.SKILL,
                    project=brief.project,
                ),
                refresh=True,
            )
        except Exception as exc:  # pragma: no cover - exact backend errors vary
            return SkillSearchResult(
                decision=SkillSearchDecision.SEARCH_UNAVAILABLE,
                query=query_text,
                candidates=[],
                recommended_action=(
                    "Run operational readiness/repair before creating a new skill "
                    "so an index failure is not mistaken for a missing skill."
                ),
                gaps=["Skill library search failed"],
                decision_explanation=_empty_decision_explanation(
                    gaps=["Skill library search failed"],
                    limitations=[f"Skill library search unavailable: {exc}"],
                ),
                handoff=_repair_handoff(error_message=str(exc)),
                search_error=str(exc),
            )

        candidates = _dedupe_candidates(hits, brief)
        if not candidates:
            return SkillSearchResult(
                decision=SkillSearchDecision.NOT_FOUND,
                query=query_text,
                candidates=[],
                recommended_action=(
                    "No reusable skill was found in healthy search; create a "
                    "draft skill-acquisition job if the capability is still needed."
                ),
                gaps=["No non-archived skill candidates matched the capability brief"],
                decision_explanation=_empty_decision_explanation(
                    gaps=[
                        "No non-archived skill candidates matched the capability brief"
                    ],
                    limitations=["No reusable skill candidate was available to score"],
                ),
            )

        top = candidates[0]
        if top.sufficiency_score >= 8 and not top.gaps:
            return SkillSearchResult(
                decision=SkillSearchDecision.FOUND_SUFFICIENT,
                query=query_text,
                candidates=candidates,
                recommended_action=(
                    f"Reuse existing skill '{top.title}' at {top.path}; do not "
                    "create a skill-acquisition job."
                ),
                gaps=[],
                decision_explanation=_decision_explanation(
                    candidates=candidates,
                    gaps=[],
                ),
                handoff=_existing_skill_handoff(candidate=top, brief=brief),
            )
        gaps = _unique_gap_list(candidates)
        return SkillSearchResult(
            decision=SkillSearchDecision.FOUND_PARTIAL,
            query=query_text,
            candidates=candidates,
            recommended_action=(
                "Related skills exist but do not fully satisfy the capability "
                "brief; pass candidates and gaps into librarian acquisition."
            ),
            gaps=gaps,
            decision_explanation=_decision_explanation(
                candidates=candidates,
                gaps=gaps,
            ),
            handoff=_existing_skill_handoff(candidate=top, brief=brief),
        )


def _query_text(brief: SkillCapabilityBrief) -> str:
    parts = [brief.capability, brief.task_goal, brief.environment]
    parts.extend(brief.required_tools)
    parts.extend(brief.success_criteria)
    return " ".join(part.strip() for part in parts if part and part.strip())


def _existing_skill_handoff(
    *,
    candidate: SkillSearchCandidate,
    brief: SkillCapabilityBrief,
) -> JSONObject:
    evidence: list[JSONValue] = [
        {
            "url_or_path": url,
            "source_kind": "skill_evidence",
            "supports_claims": candidate.why_match,
        }
        for url in candidate.evidence
    ]
    return {
        "decision": "existing_skill_found",
        "skill": {
            "id": candidate.id,
            "title": candidate.title,
            "path": candidate.path,
            "status": candidate.status,
            "version": candidate.version,
            "risk_level": candidate.risk_level.value,
            "required_tools": candidate.required_tools,
        },
        "evidence": evidence,
        "reuse": {
            "sufficiency_score": candidate.sufficiency_score,
            "matched_terms": candidate.matched_terms,
            "why_match": candidate.why_match,
            "limitations": candidate.limitations,
        },
        "current_task": {
            "resume_summary": brief.task_goal or brief.capability,
            "next_steps": [
                f"Open and apply existing skill note: {candidate.path}",
                "Do not start librarian acquisition for this capability unless reuse fails.",
            ],
            "stop_condition": (
                "Stop when the existing skill has been applied to the current "
                "task or when a concrete limitation blocks reuse."
            ),
        },
    }


def _repair_handoff(*, error_message: str) -> JSONObject:
    return {
        "decision": "skill_search_repair_required",
        "repair": {
            "hint": (
                "Repair Obsidian search/readiness before starting skill acquisition "
                "so index failure is not mistaken for a missing skill."
            ),
            "error": error_message,
            "tools": [
                "alexandria_librarian_readiness",
                "alexandria_reindex_vault",
            ],
        },
    }


def _empty_decision_explanation(
    *,
    gaps: list[str],
    limitations: list[str],
) -> JSONObject:
    return {
        "candidate_count": 0,
        "candidate_ids": [],
        "scores": [],
        "hard_gates": {},
        "match_reasons": {},
        "gaps": gaps,
        "limitations": limitations,
    }


def _decision_explanation(
    *,
    candidates: list[SkillSearchCandidate],
    gaps: list[str],
) -> JSONObject:
    return {
        "candidate_count": len(candidates),
        "candidate_ids": [candidate.id for candidate in candidates],
        "scores": [
            {
                "id": candidate.id,
                "sufficiency_score": candidate.sufficiency_score,
            }
            for candidate in candidates
        ],
        "hard_gates": {candidate.id: candidate.hard_gates for candidate in candidates},
        "match_reasons": {
            candidate.id: candidate.why_match for candidate in candidates
        },
        "gaps": gaps,
        "limitations": {
            candidate.id: candidate.limitations for candidate in candidates
        },
    }


def _dedupe_candidates(
    hits: list[ObsidianSearchHit],
    brief: SkillCapabilityBrief,
) -> list[SkillSearchCandidate]:
    candidates: list[SkillSearchCandidate] = []
    seen: set[str] = set()
    for hit in hits:
        note = hit.note
        if note.note_id in seen:
            continue
        seen.add(note.note_id)
        status = _skill_status(note.status, note.frontmatter)
        if status in {"archived", "deprecated", "superseded"}:
            continue
        candidates.append(_candidate_from_hit(hit, brief, status))
    candidates.sort(
        key=lambda candidate: (-candidate.sufficiency_score, -candidate.score)
    )
    return candidates


def _candidate_from_hit(
    hit: ObsidianSearchHit,
    brief: SkillCapabilityBrief,
    status: str,
) -> SkillSearchCandidate:
    note = hit.note
    required_tools = _string_list(note.frontmatter.get("required_tools"))
    risk_level = _risk_level(note.frontmatter.get("risk_level"))
    risk_tolerance = _risk_level(brief.risk_tolerance)
    evidence = _string_list(note.frontmatter.get("evidence_urls"))
    if not evidence:
        evidence = _evidence_from_body(note.body)
    matched_terms = _matched_terms(brief, f"{note.title}\n{hit.excerpt}\n{note.body}")
    gaps: list[str] = []
    why_match: list[str] = []

    if status != "active":
        gaps.append(f"skill status is {status}; human review is required before reuse")
    else:
        why_match.append("skill status is active")

    missing_tools = sorted(
        set(_lower_items(brief.required_tools)) - set(_lower_items(required_tools))
    )
    if missing_tools:
        gaps.append("missing required tools: " + ", ".join(missing_tools))
    else:
        why_match.append("required tools are compatible")

    if _risk_rank(risk_level) > _risk_rank(risk_tolerance):
        gaps.append(
            f"risk level {risk_level.value} exceeds tolerance {risk_tolerance.value}"
        )
    else:
        why_match.append("risk level is within tolerance")

    if not _has_procedure(note.body):
        gaps.append("skill body lacks a concrete Procedure section")
    else:
        why_match.append("body includes a concrete Procedure section")

    if not matched_terms:
        gaps.append(
            "candidate matched search index but no brief terms were found in note"
        )
    else:
        why_match.append(
            "candidate matched brief terms: " + ", ".join(matched_terms[:5])
        )

    if not evidence:
        gaps.append("skill lacks evidence links")
    else:
        why_match.append("skill includes evidence links")

    score = _candidate_score(
        matched_terms=matched_terms,
        has_procedure=_has_procedure(note.body),
        has_evidence=bool(evidence),
        project_match=brief.project is None or brief.project == note.project,
        tool_match=not missing_tools,
    )
    sufficiency_score = max(0, min(10, score - (2 * len(gaps))))
    limitations = list(gaps)
    recommended_action = (
        "Reuse this skill for the current task."
        if not gaps and sufficiency_score >= 8
        else "Use as context for librarian acquisition; do not auto-apply as sufficient."
    )
    return SkillSearchCandidate(
        id=note.note_id,
        path=note.relative_path,
        title=note.title,
        status=status,
        version=_optional_string(note.frontmatter.get("version")),
        project=note.project,
        required_tools=required_tools,
        risk_level=risk_level,
        evidence=evidence,
        matched_terms=matched_terms,
        limitations=limitations,
        score=hit.score,
        sufficiency_score=sufficiency_score,
        hard_gates=_hard_gates(
            status=status,
            missing_tools=missing_tools,
            risk_level=risk_level,
            risk_tolerance=risk_tolerance,
            has_procedure=_has_procedure(note.body),
            matched_terms=matched_terms,
            has_evidence=bool(evidence),
        ),
        why_match=why_match,
        gaps=gaps,
        recommended_action=recommended_action,
    )


def _hard_gates(
    *,
    status: str,
    missing_tools: list[str],
    risk_level: RiskLevel,
    risk_tolerance: RiskLevel,
    has_procedure: bool,
    matched_terms: list[str],
    has_evidence: bool,
) -> JSONObject:
    return {
        "active_status": {
            "passed": status == "active",
            "actual": status,
            "required": "active",
        },
        "required_tools": {
            "passed": not missing_tools,
            "missing": missing_tools,
        },
        "risk_tolerance": {
            "passed": _risk_rank(risk_level) <= _risk_rank(risk_tolerance),
            "actual": risk_level.value,
            "maximum": risk_tolerance.value,
        },
        "procedure_section": {
            "passed": has_procedure,
        },
        "brief_match": {
            "passed": bool(matched_terms),
            "matched_terms": matched_terms,
        },
        "evidence": {
            "passed": has_evidence,
        },
    }


def _candidate_score(
    *,
    matched_terms: list[str],
    has_procedure: bool,
    has_evidence: bool,
    project_match: bool,
    tool_match: bool,
) -> int:
    score = 0
    score += min(2, len(matched_terms))
    score += 2 if project_match else 0
    score += 2 if has_procedure else 0
    score += 2 if tool_match else 0
    score += 2 if has_evidence else 1
    return score


def _skill_status(status: str, frontmatter: object) -> str:
    if isinstance(frontmatter, dict):
        for key in ("skill_status", "status", "requested_status"):
            value = frontmatter.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip().lower()
    return status.strip().lower()


def _risk_level(value: object) -> RiskLevel:
    if isinstance(value, RiskLevel):
        return value
    if isinstance(value, str):
        normalized = value.strip().upper()
        for risk in RiskLevel:
            if normalized == risk.value:
                return risk
    return RiskLevel.LOW


def _risk_rank(value: RiskLevel) -> int:
    return {RiskLevel.LOW: 0, RiskLevel.MEDIUM: 1, RiskLevel.HIGH: 2}[value]


def _has_procedure(body: str) -> bool:
    match = re.search(
        r"^##+\s+.*(Procedure|단계별 절차).*$",
        body,
        flags=re.IGNORECASE | re.MULTILINE,
    )
    if match is None:
        return False
    section = body[match.end() :]
    next_heading = re.search(r"^##+\s+", section, flags=re.MULTILINE)
    if next_heading is not None:
        section = section[: next_heading.start()]
    stripped = section.strip()
    return bool(stripped and stripped != "- none provided")


def _matched_terms(brief: SkillCapabilityBrief, haystack: str) -> list[str]:
    needles = [brief.capability, *brief.required_tools]
    if brief.environment:
        needles.append(brief.environment)
    if brief.task_goal:
        needles.extend(_important_words(brief.task_goal))
    haystack_lower = haystack.lower()
    matched: list[str] = []
    for needle in needles:
        normalized = needle.strip().lower()
        if normalized and normalized in haystack_lower and normalized not in matched:
            matched.append(normalized)
    return matched


def _important_words(value: str) -> list[str]:
    return list(re.findall(r"[A-Za-z0-9_-]{4,}", value.lower())[:8])


def _evidence_from_body(body: str) -> list[str]:
    urls = re.findall(r"https?://[^\s)]+", body)
    return urls[:5]


def _string_list(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    items: list[str] = []
    for item in value:
        normalized = item.strip() if isinstance(item, str) else ""
        if normalized and normalized not in items:
            items.append(normalized)
    return items


def _lower_items(values: list[str]) -> list[str]:
    return [value.strip().lower() for value in values if value.strip()]


def _optional_string(value: object) -> str | None:
    if isinstance(value, str) and value.strip():
        return value.strip()
    return None


def _unique_gap_list(candidates: list[SkillSearchCandidate]) -> list[str]:
    gaps: list[str] = []
    for candidate in candidates:
        for gap in candidate.gaps:
            if gap not in gaps:
                gaps.append(gap)
    return gaps
