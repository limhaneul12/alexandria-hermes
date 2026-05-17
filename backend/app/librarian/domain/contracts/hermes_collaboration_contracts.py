"""Internal contracts for Hermes librarian collaboration flows."""

from __future__ import annotations

from dataclasses import dataclass

from app.librarian.domain.event_enum.collaboration_enums import (
    AcquisitionDecision,
    LibrarianDelegateKind,
    LibrarianDelegateStatus,
    LibrarianDelegationStatus,
)


@dataclass(frozen=True, slots=True, kw_only=True)
class HermesLibrarianAskCommand:
    """Command produced when Hermes asks the librarian for work guidance."""

    prompt: str
    agent_name: str
    project: str | None
    task_summary: str | None
    delegate_to_librarian: bool
    provider_id: str | None
    librarian_profile_id: str | None
    librarian_model: str | None
    librarian_role_prompt: str | None
    max_librarian_agents: int | None
    routing_specialties: list[str]
    librarian_brief: str | None = None


@dataclass(frozen=True, slots=True, kw_only=True)
class LibrarianDelegateResult:
    """Result from one synchronous librarian delegate lane."""

    profile_id: str
    provider_id: str | None
    status: LibrarianDelegateStatus
    delegate_type: LibrarianDelegateKind
    summary: str
    matched_specialties: list[str]


@dataclass(frozen=True, slots=True, kw_only=True)
class HermesLibrarianAskResult:
    """Result returned to Hermes after an ask/delegation request."""

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
    delegates: list[LibrarianDelegateResult]


@dataclass(frozen=True, slots=True, kw_only=True)
class LibrarianJobStatusResult:
    """Guidance-only job status result returned by job-status reads."""

    job_id: str
    status: LibrarianDelegationStatus
    result_available: bool
    message: str
