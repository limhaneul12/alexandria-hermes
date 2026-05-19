"""Durable skill-acquisition job read models."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from app.librarian.domain.event_enum.collaboration_enums import (
    SkillAcquisitionJobStatus,
)


@dataclass(frozen=True, slots=True)
class SkillAcquisitionJob:
    """Read model for one librarian-owned skill-acquisition job."""

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
    created_at: datetime
    updated_at: datetime
    completed_at: datetime | None

    @property
    def result_available(self) -> bool:
        """Return whether the job produced a persisted result.

        Returns:
            True when a skill or context result is available.
        """
        return self.skill_id is not None or self.context_id is not None
