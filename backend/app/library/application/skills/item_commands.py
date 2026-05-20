"""Skill item-service command builders."""

from __future__ import annotations

from app.library.application.skills.payload_mapper import (
    build_agent_skill_details,
    build_librarian_skill_item_payload,
    build_skill_details,
)
from app.library.domain.contracts.skill_candidate_contracts import (
    CreateSkillCandidateResult,
)
from app.library.domain.contracts.skill_item_contracts import (
    SkillCreateFields,
    SkillItemCreateCommand,
)
from app.library.domain.event_enum.item_enums import (
    CreatedByType,
    ItemStatus,
    ItemType,
    SourceType,
)
from app.shared.exceptions import LibraryValidationError
from app.shared.types.types_convert_utils import enum_value


def build_user_skill_create_command(
    fields: SkillCreateFields,
) -> SkillItemCreateCommand:
    """Build a create-item command for a manually submitted skill.

    Args:
        fields: Common public skill creation fields.

    Returns:
        Item-service create command for user-created skills.
    """
    _validate_required_source_fields(fields=fields)
    command = _build_skill_create_command(
        fields=fields,
        source_type=SourceType.USER_CREATED,
        created_by_type=CreatedByType.USER,
    )
    return command


def build_agent_skill_create_command(
    fields: SkillCreateFields,
) -> SkillItemCreateCommand:
    """Build a create-item command for an agent-submitted skill.

    Args:
        fields: Common public skill creation fields.

    Returns:
        Item-service create command for agent-submitted skills.
    """
    _validate_required_source_fields(fields=fields)
    status = _initial_skill_status(fields)
    evidence_urls = _candidate_evidence_urls(fields)
    command = SkillItemCreateCommand(
        item_type=ItemType.SKILL,
        title=fields.title,
        summary=fields.summary,
        content=fields.content,
        category_id=fields.category_id,
        tags=fields.tags,
        status=status,
        source_type=SourceType.AGENT_SUBMITTED,
        created_by_type=CreatedByType.AGENT,
        created_by_name=fields.created_by_name,
        details=build_agent_skill_details(
            title=fields.title,
            purpose=fields.purpose,
            content=fields.content,
            input_schema=fields.input_schema,
            output_schema=fields.output_schema,
            usage_example=fields.usage_example,
            required_tools=fields.required_tools,
            risk_level=fields.risk_level,
            version=fields.version,
            evidence_urls=evidence_urls,
            source_summary=fields.source_summary,
        ),
    )
    return command


def build_librarian_skill_create_command(
    generated: CreateSkillCandidateResult,
    category_id: str | None,
    tags: list[str],
    created_by_name: str,
) -> SkillItemCreateCommand:
    """Build a create-item command for a librarian-generated skill draft.

    Args:
        generated: Candidate payload from provider adapter.
        category_id: Optional category.
        tags: Tag list.
        created_by_name: Source display name.

    Returns:
        Item-service create command for librarian-created skills.
    """
    if not created_by_name.strip():
        raise LibraryValidationError("created_by_name is required")

    item_payload = build_librarian_skill_item_payload(
        generated=generated,
        category_id=category_id,
        tags=tags,
        created_by_name=created_by_name,
    )
    command = SkillItemCreateCommand(
        item_type=ItemType.SKILL,
        title=item_payload["title"],
        summary=item_payload["summary"],
        content=item_payload["content"],
        category_id=item_payload["category_id"],
        tags=item_payload["tags"],
        status=ItemStatus.DRAFT,
        source_type=SourceType.LIBRARIAN_CREATED,
        created_by_type=CreatedByType.LIBRARIAN,
        created_by_name=created_by_name,
        details=item_payload["details"],
    )
    return command


def _build_skill_create_command(
    fields: SkillCreateFields,
    source_type: SourceType,
    created_by_type: CreatedByType,
) -> SkillItemCreateCommand:
    status = _initial_skill_status(fields)
    command = SkillItemCreateCommand(
        item_type=ItemType.SKILL,
        title=fields.title,
        summary=fields.summary,
        content=fields.content,
        category_id=fields.category_id,
        tags=fields.tags,
        status=status,
        source_type=source_type,
        created_by_type=created_by_type,
        created_by_name=fields.created_by_name,
        details=build_skill_details(
            purpose=fields.purpose,
            input_schema=fields.input_schema,
            output_schema=fields.output_schema,
            usage_example=fields.usage_example,
            required_tools=fields.required_tools,
            risk_level=fields.risk_level,
            version=fields.version,
        ),
    )
    return command


def _initial_skill_status(fields: SkillCreateFields) -> ItemStatus:
    status = fields.status
    if status is None:
        status = ItemStatus.ACTIVE if fields.activate else ItemStatus.DRAFT
    status = enum_value(status, ItemStatus, "status")
    return status


def _candidate_evidence_urls(fields: SkillCreateFields) -> list[str]:
    evidence_urls: list[str] = []
    if fields.evidence_urls is not None:
        evidence_urls = list(fields.evidence_urls)
    return evidence_urls


def _validate_required_source_fields(fields: SkillCreateFields) -> None:
    if not fields.purpose.strip():
        raise LibraryValidationError("purpose is required")
    if not fields.created_by_name.strip():
        raise LibraryValidationError("created_by_name is required")
