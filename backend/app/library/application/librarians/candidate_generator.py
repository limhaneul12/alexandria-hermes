"""Deterministic librarian candidate generation."""

from __future__ import annotations

import hashlib

from app.library.domain.contracts.librarian_candidate_contracts import (
    CreateSkillCandidateResult,
)
from app.library.domain.event_enum.skill_enums import RiskLevel


def build_candidate_stub(
    provider_id: str,
    prompt: str,
    seed: int | None = None,
) -> CreateSkillCandidateResult:
    """Generate deterministic skill candidate payload for a prompt.

    Args:
        provider_id: Provider id used by caller.
        prompt: Natural-language request.
        seed: Optional deterministic seed.

    Returns:
        Candidate result.
    """
    normalized = prompt.strip().replace("\n", " ")
    seed_text = "" if seed is None else str(seed)
    digest = hashlib.sha256(
        f"{provider_id}:{normalized}:{seed_text}".encode()
    ).hexdigest()[:8]
    title_prefix = normalized[:60] if normalized else "Generated skill"
    title = f"{title_prefix} [{digest}]"
    candidate_result = CreateSkillCandidateResult(
        title=title,
        summary=f"Auto-generated skill candidate ({digest})",
        content=f"Generated skill from librarian {provider_id}: {normalized}",
        purpose=normalized,
        input_schema={
            "type": "object",
            "properties": {
                "request": {
                    "type": "string",
                },
            },
        },
        output_schema={
            "type": "object",
            "properties": {
                "result": {
                    "type": "string",
                },
            },
        },
        required_tools=["planner"],
        risk_level=RiskLevel.LOW,
        version="1.0.0",
        prompt=normalized,
        provider_id=provider_id,
    )
    return candidate_result
