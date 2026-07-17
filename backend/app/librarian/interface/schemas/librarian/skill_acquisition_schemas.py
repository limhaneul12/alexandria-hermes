"""Skill-acquisition job API schemas."""

from __future__ import annotations

from typing import Annotated, cast

from pydantic import Field, StringConstraints

from app.librarian.application.skill_library_search_service import (
    SkillCapabilityBrief,
    SkillSearchCandidate,
    SkillSearchDecision,
    SkillSearchResult,
)
from app.librarian.domain.contracts.skill_acquisition_contracts import (
    SkillAcquisitionArtifact,
    SkillAcquisitionEvidenceItem,
)
from app.librarian.domain.entities.skill_acquisition_job import SkillAcquisitionJob
from app.librarian.domain.event_enum.collaboration_enums import (
    SkillAcquisitionJobStage,
    SkillAcquisitionJobStatus,
)
from app.librarian.domain.event_enum.skill_acquisition_enums import (
    ItemStatus,
    RiskLevel,
)
from app.librarian.domain.types.skill_acquisition_payload_types import (
    SkillSchemaPayload,
)
from app.shared.schemas.common_schemas import StrictSchemaModel
from app.shared.schemas.datetime_schemas import AwareTimestamp
from app.shared.types.extra_types import JSONValue

NonBlankString = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


class SkillAcquisitionJobRequest(StrictSchemaModel):
    """Request payload for creating a durable skill-acquisition job."""

    prompt: str = Field(min_length=1)
    agent_name: str = Field(default="Hermes", min_length=1)
    project: str | None = None
    task_summary: str | None = None
    provider_id: str | None = None
    librarian_profile_id: str | None = None
    search_snapshot: dict[str, JSONValue] | None = None
    acquisition_override_reason: str | None = None


class SkillAcquisitionEvidenceItemRequest(StrictSchemaModel):
    """Claim-linked evidence item for acquired skill completion."""

    url_or_path: NonBlankString
    title: str | None = None
    source_kind: str | None = None
    publisher_or_repository: str | None = None
    accessed_at: str | None = None
    supports_claims: list[str] = Field(default_factory=list)
    freshness: str | None = None
    notes: str | None = None

    def to_evidence_item(self) -> SkillAcquisitionEvidenceItem:
        """Return the internal evidence item command.

        Returns:
            Internal skill-acquisition evidence item.
        """
        return SkillAcquisitionEvidenceItem(
            url_or_path=self.url_or_path,
            title=self.title,
            source_kind=self.source_kind,
            publisher_or_repository=self.publisher_or_repository,
            accessed_at=self.accessed_at,
            supports_claims=list(self.supports_claims),
            freshness=self.freshness,
            notes=self.notes,
        )


class SkillAcquisitionCompletionRequest(StrictSchemaModel):
    """Structured acquired skill artifact used to complete a durable job."""

    title: NonBlankString
    purpose: NonBlankString
    content: NonBlankString
    summary: str | None = None
    category_id: str | None = None
    tags: list[str] = Field(default_factory=list)
    input_schema: dict[str, JSONValue] = Field(default_factory=dict)
    output_schema: dict[str, JSONValue] = Field(default_factory=dict)
    usage_example: str | None = None
    required_tools: list[str] = Field(default_factory=list)
    risk_level: RiskLevel = RiskLevel.LOW
    version: str = "1.0.0"
    created_by_name: str | None = None
    activate: bool = False
    status: ItemStatus = ItemStatus.DRAFT
    evidence_urls: list[str] = Field(default_factory=list)
    evidence_items: list[SkillAcquisitionEvidenceItemRequest] = Field(
        default_factory=list
    )
    source_summary: str | None = None
    next_steps: list[str] = Field(default_factory=list)

    def to_artifact(self) -> SkillAcquisitionArtifact:
        """Return the internal completion artifact command.

        Returns:
            Internal skill-acquisition artifact.
        """
        return SkillAcquisitionArtifact(
            title=self.title,
            purpose=self.purpose,
            content=self.content,
            summary=self.summary,
            category_id=self.category_id,
            tags=list(self.tags),
            input_schema=cast(SkillSchemaPayload, self.input_schema),
            output_schema=cast(SkillSchemaPayload, self.output_schema),
            usage_example=self.usage_example,
            required_tools=list(self.required_tools),
            risk_level=self.risk_level,
            version=self.version,
            created_by_name=self.created_by_name,
            activate=self.activate,
            status=self.status,
            evidence_urls=list(self.evidence_urls),
            evidence_items=[item.to_evidence_item() for item in self.evidence_items],
            source_summary=self.source_summary,
            next_steps=list(self.next_steps),
        )


class SkillAcquisitionJobResponse(StrictSchemaModel):
    """Public response for one durable skill-acquisition job."""

    id: str
    prompt: str
    agent_name: str
    project: str | None
    task_summary: str | None
    status: SkillAcquisitionJobStatus
    provider_id: str | None
    librarian_profile_id: str | None
    skill_id: str | None
    context_id: str | None
    result_summary: str | None
    evidence_urls: list[str]
    error_message: str | None
    result_available: bool
    created_at: AwareTimestamp
    updated_at: AwareTimestamp
    completed_at: AwareTimestamp | None
    stage: SkillAcquisitionJobStage | None
    progress_summary: str | None
    skill_note_path: str | None
    reindex_status: str | None
    verification_status: str | None
    handoff: dict[str, JSONValue] | None
    repair_hint: str | None
    search_snapshot: dict[str, JSONValue] | None
    acquisition_override_reason: str | None
    prompt_reference: str | None
    prompt_reference_hash: str | None


def skill_acquisition_job_response(
    job: SkillAcquisitionJob,
) -> SkillAcquisitionJobResponse:
    """Map a job read model into a public response schema.

    Args:
        job: Durable job read model.

    Returns:
        Public API response schema.
    """
    response = SkillAcquisitionJobResponse(
        id=job.id,
        prompt=job.prompt,
        agent_name=job.agent_name,
        project=job.project,
        task_summary=job.task_summary,
        status=job.status,
        provider_id=job.provider_id,
        librarian_profile_id=job.librarian_profile_id,
        skill_id=job.skill_id,
        context_id=job.context_id,
        result_summary=job.result_summary,
        evidence_urls=job.evidence_urls,
        error_message=job.error_message,
        result_available=job.result_available,
        created_at=job.created_at,
        updated_at=job.updated_at,
        completed_at=job.completed_at,
        stage=job.stage,
        progress_summary=job.progress_summary,
        skill_note_path=job.skill_note_path,
        reindex_status=job.reindex_status,
        verification_status=job.verification_status,
        handoff=job.handoff,
        repair_hint=job.repair_hint,
        search_snapshot=job.search_snapshot,
        acquisition_override_reason=job.acquisition_override_reason,
        prompt_reference=job.prompt_reference,
        prompt_reference_hash=job.prompt_reference_hash,
    )
    return response


class SkillCapabilitySearchRequest(StrictSchemaModel):
    """Search-first request before creating a skill-acquisition job."""

    capability: str = Field(min_length=1)
    task_goal: str | None = None
    project: str | None = None
    environment: str | None = None
    required_tools: list[str] = Field(default_factory=list)
    constraints: list[str] = Field(default_factory=list)
    risk_tolerance: RiskLevel = RiskLevel.MEDIUM
    success_criteria: list[str] = Field(default_factory=list)
    limit: int = Field(default=5, ge=1, le=10)

    def to_brief(self) -> SkillCapabilityBrief:
        """Return the internal normalized capability brief.

        Returns:
            Application search brief.
        """
        return SkillCapabilityBrief(
            capability=self.capability,
            task_goal=self.task_goal,
            project=self.project,
            environment=self.environment,
            required_tools=list(self.required_tools),
            constraints=list(self.constraints),
            risk_tolerance=self.risk_tolerance,
            success_criteria=list(self.success_criteria),
            limit=self.limit,
        )


class SkillSearchCandidateResponse(StrictSchemaModel):
    """Normalized skill candidate returned by search-first evaluation."""

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
    hard_gates: dict[str, JSONValue]
    why_match: list[str]
    gaps: list[str]
    recommended_action: str


class SkillCapabilitySearchResponse(StrictSchemaModel):
    """Search-first sufficiency result for one capability brief."""

    decision: SkillSearchDecision
    query: str
    candidates: list[SkillSearchCandidateResponse]
    recommended_action: str
    gaps: list[str]
    decision_explanation: dict[str, JSONValue]
    handoff: dict[str, JSONValue] | None
    search_error: str | None


def skill_search_candidate_response(
    candidate: SkillSearchCandidate,
) -> SkillSearchCandidateResponse:
    """Map one application candidate to the public response schema.

    Args:
        candidate: Application search candidate.

    Returns:
        Public candidate response schema.
    """
    return SkillSearchCandidateResponse(
        id=candidate.id,
        path=candidate.path,
        title=candidate.title,
        status=candidate.status,
        version=candidate.version,
        project=candidate.project,
        required_tools=candidate.required_tools,
        risk_level=candidate.risk_level,
        evidence=candidate.evidence,
        matched_terms=candidate.matched_terms,
        limitations=candidate.limitations,
        score=candidate.score,
        sufficiency_score=candidate.sufficiency_score,
        hard_gates=candidate.hard_gates,
        why_match=candidate.why_match,
        gaps=candidate.gaps,
        recommended_action=candidate.recommended_action,
    )


def skill_capability_search_response(
    result: SkillSearchResult,
) -> SkillCapabilitySearchResponse:
    """Map application search result to public response schema.

    Args:
        result: Application search result.

    Returns:
        Public search response schema.
    """
    return SkillCapabilitySearchResponse(
        decision=result.decision,
        query=result.query,
        candidates=[
            skill_search_candidate_response(candidate)
            for candidate in result.candidates
        ],
        recommended_action=result.recommended_action,
        gaps=result.gaps,
        decision_explanation=result.decision_explanation,
        handoff=result.handoff,
        search_error=result.search_error,
    )
