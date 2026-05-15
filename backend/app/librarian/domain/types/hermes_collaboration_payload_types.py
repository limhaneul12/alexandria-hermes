"""Typed payload contracts for Hermes librarian collaboration responses."""

from __future__ import annotations

from app.librarian.domain.event_enum.collaboration_enums import (
    AcquisitionDecision,
    LibrarianDelegateKind,
    LibrarianDelegateStatus,
    LibrarianDelegationStatus,
)
from typing_extensions import TypedDict


class LibrarianDelegatePayload(TypedDict, closed=True):
    """Public payload for one synchronous delegate lane."""

    profile_id: str
    provider_id: str | None
    status: LibrarianDelegateStatus
    delegate_type: LibrarianDelegateKind
    summary: str
    matched_specialties: list[str]


class HermesLibrarianAskPayload(TypedDict, closed=True):
    """Public ask-librarian response payload."""

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
    delegates: list[LibrarianDelegatePayload]


class LibrarianJobStatusPayload(TypedDict, closed=True):
    """Public librarian job status payload."""

    job_id: str
    status: LibrarianDelegationStatus
    result_available: bool
    message: str
