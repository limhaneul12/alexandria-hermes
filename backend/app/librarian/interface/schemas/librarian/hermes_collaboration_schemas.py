"""Schemas for Hermes librarian collaboration endpoints."""

from __future__ import annotations

from app.librarian.domain.contracts.hermes_collaboration_contracts import (
    HermesLibrarianAskCommand,
)
from app.librarian.domain.event_enum.collaboration_enums import (
    AcquisitionDecision,
    LibrarianDelegateKind,
    LibrarianDelegateStatus,
    LibrarianDelegationStatus,
)
from app.librarian.interface.schemas.librarian.librarian_brief_schemas import (
    BudgetPolicySchema,
    ContextPackCompactSchema,
    SourceRefSchema,
)
from app.shared.schemas.common_schemas import StrictSchemaModel
from pydantic import ConfigDict, Field


class AskLibrarianRequest(StrictSchemaModel):
    """Request for Hermes missing-capability collaboration guidance."""

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "prompt": "Need a skill for reviewing OAuth callbacks.",
                    "agent_name": "Hermes",
                    "project": "alexandria-hermes",
                    "task_summary": "Implement provider OAuth flow",
                    "delegate_to_librarian": False,
                    "provider_id": None,
                    "librarian_profile_id": None,
                    "librarian_model": "gpt-5.5",
                    "librarian_role_prompt": "Use project memory before web search.",
                    "max_librarian_agents": 2,
                    "routing_specialties": ["fastapi", "oauth"],
                }
            ]
        }
    )

    prompt: str = Field(min_length=1)
    agent_name: str = "Hermes"
    project: str | None = None
    task_summary: str | None = None
    delegate_to_librarian: bool = False
    provider_id: str | None = None
    librarian_profile_id: str | None = None
    librarian_model: str | None = None
    librarian_role_prompt: str | None = Field(default=None, max_length=4096)
    max_librarian_agents: int | None = Field(default=None, ge=1, le=6)
    routing_specialties: list[str] = Field(default_factory=list)
    budget: BudgetPolicySchema = Field(default_factory=BudgetPolicySchema)
    context_compact: ContextPackCompactSchema | None = None
    source_refs: list[SourceRefSchema] = Field(default_factory=list)

    def to_command(self, *, librarian_brief: str | None) -> HermesLibrarianAskCommand:
        """Return an application command for the collaboration service.

        Args:
            librarian_brief: Precompiled delegate brief from the application layer.

        Returns:
            HermesLibrarianAskCommand: Internal command DTO.
        """
        command = HermesLibrarianAskCommand(
            prompt=self.prompt,
            agent_name=self.agent_name,
            project=self.project,
            task_summary=self.task_summary,
            delegate_to_librarian=self.delegate_to_librarian,
            provider_id=self.provider_id,
            librarian_profile_id=self.librarian_profile_id,
            librarian_model=self.librarian_model,
            librarian_role_prompt=self.librarian_role_prompt,
            max_librarian_agents=self.max_librarian_agents,
            routing_specialties=self.routing_specialties,
            librarian_brief=librarian_brief,
        )
        return command


class LibrarianDelegateResponse(StrictSchemaModel):
    """Response item for one synchronous librarian delegate lane."""

    profile_id: str
    provider_id: str | None
    status: LibrarianDelegateStatus
    delegate_type: LibrarianDelegateKind
    summary: str
    matched_specialties: list[str]


class AskLibrarianResponse(StrictSchemaModel):
    """Response describing Hermes self-acquisition or delegation guidance."""

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "job_id": "librarian-job-abc123",
                    "status": "GUIDANCE_ONLY",
                    "decision": "SUGGEST_HERMES_RESEARCH",
                    "librarian_available": False,
                    "self_acquisition_allowed": True,
                    "recommendation": "Hermes can research and submit a candidate.",
                    "provider_id": None,
                    "candidate_id": None,
                    "librarian_profile_id": None,
                    "librarian_model": None,
                    "librarian_role_prompt": None,
                    "max_librarian_agents": None,
                    "selected_profiles": [],
                    "matched_specialties": [],
                    "quality_review_added": False,
                    "routing_reason": "No executable librarian provider available",
                    "delegates": [],
                }
            ]
        }
    )

    job_id: str
    status: LibrarianDelegationStatus
    decision: AcquisitionDecision
    librarian_available: bool
    self_acquisition_allowed: bool
    recommendation: str
    provider_id: str | None
    candidate_id: str | None
    librarian_profile_id: str | None
    librarian_model: str | None
    librarian_role_prompt: str | None
    max_librarian_agents: int | None
    route_preview: list[str]
    selected_profiles: list[str]
    matched_specialties: list[str]
    quality_review_added: bool
    routing_reason: str
    delegates: list[LibrarianDelegateResponse]


class LibrarianJobStatusResponse(StrictSchemaModel):
    """Response for a Hermes librarian job status lookup."""

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "job_id": "librarian-job-abc123",
                    "status": "GUIDANCE_ONLY",
                    "result_available": False,
                    "message": (
                        "No durable librarian job is queued yet; ask responses are "
                        "guidance-only until executor persistence is implemented."
                    ),
                }
            ]
        }
    )

    job_id: str
    status: LibrarianDelegationStatus
    result_available: bool
    message: str
