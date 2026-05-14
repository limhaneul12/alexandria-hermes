"""Librarian candidate generation contracts."""

from __future__ import annotations

from dataclasses import dataclass

from app.library.domain.event_enum.skill_enums import RiskLevel
from app.library.domain.types.skill_payload_types import (
    SkillCandidatePayload,
    SkillSchemaPayload,
)


@dataclass(frozen=True, slots=True, kw_only=True)
class CreateSkillCandidateResult:
    """Typed result returned by deterministic librarian candidate generation."""

    title: str
    summary: str
    content: str
    purpose: str
    input_schema: SkillSchemaPayload
    output_schema: SkillSchemaPayload
    required_tools: list[str]
    risk_level: RiskLevel
    version: str
    prompt: str
    provider_id: str

    def to_candidate_payload(self) -> SkillCandidatePayload:
        """Return item creation fields consumed by skill use cases.

        Returns:
            SkillCandidatePayload: Candidate fields for skill item creation.
        """
        payload: SkillCandidatePayload = {
            "title": self.title,
            "summary": self.summary,
            "content": self.content,
            "purpose": self.purpose,
            "input_schema": self.input_schema,
            "output_schema": self.output_schema,
            "required_tools": self.required_tools,
            "risk_level": self.risk_level.value,
            "version": self.version,
            "prompt": self.prompt,
            "provider_id": self.provider_id,
        }
        return payload
