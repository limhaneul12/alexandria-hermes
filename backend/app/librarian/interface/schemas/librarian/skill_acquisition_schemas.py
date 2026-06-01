"""Skill-acquisition job API schemas."""

from __future__ import annotations

from typing import cast

from app.librarian.domain.contracts.skill_acquisition_contracts import (
    SkillAcquisitionArtifact,
)
from app.librarian.domain.entities.skill_acquisition_job import SkillAcquisitionJob
from app.librarian.domain.event_enum.collaboration_enums import (
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
from pydantic import Field


class SkillAcquisitionJobRequest(StrictSchemaModel):
    """Request payload for creating a durable skill-acquisition job."""

    prompt: str = Field(min_length=1)
    agent_name: str = Field(default="Hermes", min_length=1)
    project: str | None = None
    task_summary: str | None = None
    provider_id: str | None = None
    librarian_profile_id: str | None = None


class SkillAcquisitionCompletionRequest(StrictSchemaModel):
    """Structured acquired skill artifact used to complete a durable job."""

    title: str = Field(min_length=1)
    purpose: str = Field(min_length=1)
    content: str = Field(min_length=1)
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
    )
    return response
