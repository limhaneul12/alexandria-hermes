"""Skill item command builder behavior tests."""

from __future__ import annotations

import pytest
from app.library.application.skills.item_commands import (
    SkillCreateFields,
    build_agent_skill_create_command,
    build_librarian_skill_create_command,
    build_user_skill_create_command,
)
from app.library.domain.contracts.skill_candidate_contracts import (
    CreateSkillCandidateResult,
)
from app.library.domain.event_enum.item_enums import (
    CreatedByType,
    ItemStatus,
    ItemType,
    SourceType,
)
from app.library.domain.event_enum.skill_enums import RiskLevel
from app.shared.exceptions import ValidationError


def _skill_create_fields(
    *,
    activate: bool = False,
    status: ItemStatus | None = None,
    purpose: str = "Capture route testing guidance.",
    created_by_name: str = "alex",
) -> SkillCreateFields:
    return SkillCreateFields(
        title="FastAPI route testing",
        summary="Route tests",
        content="Use dependency overrides.",
        category_id="category-123",
        tags=["fastapi"],
        purpose=purpose,
        input_schema={"type": "object"},
        output_schema={"type": "object"},
        usage_example=None,
        required_tools=["pytest"],
        risk_level="LOW",
        version="1.0.0",
        created_by_name=created_by_name,
        activate=activate,
        status=status,
    )


def test_user_skill_create_command_preserves_user_source_contract() -> None:
    """User skill command should include manual source metadata and details."""
    command = build_user_skill_create_command(
        _skill_create_fields(status=ItemStatus.ARCHIVED)
    )

    assert command.item_type == ItemType.SKILL
    assert command.status == ItemStatus.ARCHIVED
    assert command.source_type == SourceType.USER_CREATED
    assert command.created_by_type == CreatedByType.USER
    assert command.created_by_name == "alex"
    assert command.details == {
        "purpose": "Capture route testing guidance.",
        "input_schema": {"type": "object"},
        "output_schema": {"type": "object"},
        "usage_example": None,
        "required_tools": ["pytest"],
        "risk_level": "LOW",
        "version": "1.0.0",
        "quality_gate": {
            "status": "NEEDS_REVIEW",
            "checks": [
                {
                    "name": "title_present",
                    "passed": True,
                    "message": "title is present",
                },
                {
                    "name": "content_present",
                    "passed": True,
                    "message": "content is present",
                },
                {
                    "name": "dangerous_command_absent",
                    "passed": True,
                    "message": "dangerous shell command marker is absent",
                },
                {
                    "name": "secret_redaction",
                    "passed": True,
                    "message": "secret content is redacted or safe",
                },
                {
                    "name": "evidence_or_summary_present",
                    "passed": False,
                    "message": "evidence URL or source summary is present",
                },
            ],
        },
    }


def test_agent_skill_create_command_uses_activate_when_status_is_omitted() -> None:
    """Agent skill command should derive active status from activate flag."""
    command = build_agent_skill_create_command(_skill_create_fields(activate=True))

    assert command.status == ItemStatus.ACTIVE
    assert command.source_type == SourceType.AGENT_SUBMITTED
    assert command.created_by_type == CreatedByType.AGENT


@pytest.mark.parametrize(
    ("purpose", "created_by_name", "message"),
    [
        ("  ", "alex", "purpose is required"),
        ("Capture route testing guidance.", "  ", "created_by_name is required"),
    ],
)
def test_skill_create_command_rejects_blank_required_fields(
    purpose: str,
    created_by_name: str,
    message: str,
) -> None:
    """Skill command builders should preserve required source field validation."""
    with pytest.raises(ValidationError, match=message):
        build_agent_skill_create_command(
            _skill_create_fields(
                purpose=purpose,
                created_by_name=created_by_name,
            )
        )


def test_librarian_skill_create_command_preserves_librarian_source_contract() -> None:
    """Librarian skill command should create draft item metadata from candidate."""
    generated = CreateSkillCandidateResult(
        title="Generated FastAPI skill",
        summary="Generated summary",
        content="Generated content",
        purpose="Generated purpose",
        input_schema={"type": "object"},
        output_schema={"type": "object"},
        required_tools=["planner"],
        risk_level=RiskLevel.LOW,
        version="1.0.0",
        provider_id="provider-123",
        prompt="Create a skill.",
    )

    command = build_librarian_skill_create_command(
        generated=generated,
        category_id="category-123",
        tags=["generated"],
        created_by_name="librarian",
    )

    assert command.item_type == ItemType.SKILL
    assert command.title == "Generated FastAPI skill"
    assert command.status == ItemStatus.DRAFT
    assert command.source_type == SourceType.LIBRARIAN_CREATED
    assert command.created_by_type == CreatedByType.LIBRARIAN
    assert command.created_by_name == "librarian"
    assert command.details["librarian_provider_id"] == "provider-123"


def test_librarian_skill_create_command_rejects_blank_creator_name() -> None:
    """Librarian skill command should preserve creator name validation."""
    with pytest.raises(ValidationError, match="created_by_name is required"):
        build_librarian_skill_create_command(
            generated=CreateSkillCandidateResult(
                title="Generated FastAPI skill",
                summary="Generated summary",
                content="Generated content",
                purpose="Generated purpose",
                input_schema={"type": "object"},
                output_schema={"type": "object"},
                required_tools=["planner"],
                risk_level=RiskLevel.LOW,
                version="1.0.0",
                provider_id="provider-123",
                prompt="Create a skill.",
            ),
            category_id=None,
            tags=[],
            created_by_name="  ",
        )
