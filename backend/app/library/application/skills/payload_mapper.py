"""Pure skill payload mapping and patch shaping."""

from __future__ import annotations

from collections.abc import Mapping
from typing import cast

from app.library.application.quality_gate import run_library_quality_gate
from app.library.application.skills.candidate_harness import (
    run_skill_candidate_harness,
)
from app.library.domain.contracts.skill_candidate_contracts import (
    CreateSkillCandidateResult,
)
from app.library.domain.event_enum.item_enums import ItemStatus, ItemType
from app.library.domain.event_enum.skill_enums import (
    SkillAcquisitionMethod,
    SkillDetailField,
)
from app.library.domain.types.item_payload_types import LibraryItemPayload
from app.library.domain.types.skill_payload_types import (
    AgentSubmittedSkillDetailsPayload,
    LibrarianSkillItemPayload,
    SkillCandidateHarnessCheckPayload,
    SkillCandidateHarnessPayload,
    SkillDetailsPatchPayload,
    SkillDetailsPayload,
    SkillItemUpdatePayload,
    SkillSchemaPayload,
)
from app.shared.exceptions import LibraryValidationError
from app.shared.types.extra_types import JSONValue
from app.shared.types.types_convert_utils import (
    enum_value,
    json_object_value,
    optional_string_value,
    required_string_value,
    string_items,
)


def _skill_schema_payload(value: JSONValue) -> SkillSchemaPayload:
    """Return an open JSON-schema object for a skill details field.

    Args:
        value: Raw JSON value from an existing item or patch payload.

    Returns:
        SkillSchemaPayload: Typed open JSON object for schema metadata.
    """
    return cast(SkillSchemaPayload, json_object_value(value))


def _skill_details_patch_payload(
    details: Mapping[str, JSONValue],
) -> SkillDetailsPatchPayload:
    """Normalize merged item details into the skill details patch contract.

    Args:
        details: Existing details merged with patch-provided detail fields.

    Returns:
        SkillDetailsPatchPayload: Partial skill details payload preserving existing keys.
    """
    payload = SkillDetailsPatchPayload()
    if "purpose" in details:
        payload["purpose"] = required_string_value(details["purpose"], "purpose")
    if "input_schema" in details:
        payload["input_schema"] = _skill_schema_payload(details["input_schema"])
    if "output_schema" in details:
        payload["output_schema"] = _skill_schema_payload(details["output_schema"])
    if "usage_example" in details:
        payload["usage_example"] = optional_string_value(details["usage_example"])
    if "required_tools" in details:
        payload["required_tools"] = string_items(details["required_tools"])
    if "risk_level" in details:
        payload["risk_level"] = required_string_value(
            details["risk_level"], "risk_level"
        )
    if "version" in details:
        payload["version"] = required_string_value(details["version"], "version")
    if "librarian_provider_id" in details:
        payload["librarian_provider_id"] = required_string_value(
            details["librarian_provider_id"], "librarian_provider_id"
        )
    if "prompt" in details:
        payload["prompt"] = required_string_value(details["prompt"], "prompt")
    if "evidence_urls" in details:
        payload["evidence_urls"] = string_items(details["evidence_urls"])
    if "source_summary" in details:
        payload["source_summary"] = optional_string_value(details["source_summary"])
    if "acquisition_method" in details:
        payload["acquisition_method"] = required_string_value(
            details["acquisition_method"], "acquisition_method"
        )
    if "harness" in details:
        payload["harness"] = _skill_candidate_harness_payload(details["harness"])
    if "quality_gate" in details and isinstance(details["quality_gate"], dict):
        payload["quality_gate"] = dict(details["quality_gate"])
    return payload


def _skill_candidate_harness_payload(
    value: JSONValue,
) -> SkillCandidateHarnessPayload:
    """Return a typed candidate harness payload from item details.

    Args:
        value: Raw harness value from existing details.

    Returns:
        SkillCandidateHarnessPayload: Validated harness details payload.

    Raises:
        LibraryValidationError: When the stored harness shape is invalid.
    """
    if not isinstance(value, dict):
        raise LibraryValidationError("harness must be an object")
    status = required_string_value(value.get("status"), "harness.status")
    checks_value = value.get("checks")
    if not isinstance(checks_value, list):
        raise LibraryValidationError("harness.checks must be a list")
    checks: list[SkillCandidateHarnessCheckPayload] = []
    for check_value in checks_value:
        if not isinstance(check_value, dict):
            raise LibraryValidationError("harness.checks items must be objects")
        passed_value = check_value.get("passed")
        if not isinstance(passed_value, bool):
            raise LibraryValidationError("harness.checks.passed must be a boolean")
        checks.append(
            SkillCandidateHarnessCheckPayload(
                name=required_string_value(
                    check_value.get("name"), "harness.checks.name"
                ),
                passed=passed_value,
                message=required_string_value(
                    check_value.get("message"), "harness.checks.message"
                ),
            )
        )
    payload = SkillCandidateHarnessPayload(status=status, checks=checks)
    return payload


def build_skill_details(
    purpose: str,
    input_schema: SkillSchemaPayload,
    output_schema: SkillSchemaPayload,
    usage_example: str | None,
    required_tools: list[str],
    risk_level: str,
    version: str,
) -> SkillDetailsPayload:
    """Build skill payload details used in persistent model.

    Args:
        purpose: Skill purpose statement.
        input_schema: Expected input data shape.
        output_schema: Expected output data shape.
        usage_example: Example run.
        required_tools: Required tools list.
        risk_level: Risk classification.
        version: Version string.

    Returns:
        Persistent details dictionary.
    """
    quality_gate = run_library_quality_gate(
        item_type=ItemType.SKILL,
        title=purpose,
        content=usage_example or purpose,
        evidence_urls=[],
        source_summary=None,
    )
    skill_details: SkillDetailsPayload = {
        "purpose": purpose,
        "input_schema": input_schema,
        "output_schema": output_schema,
        "usage_example": usage_example,
        "required_tools": required_tools,
        "risk_level": risk_level,
        "version": version,
        "quality_gate": quality_gate.to_payload(),
    }
    return skill_details


def build_agent_skill_details(
    title: str,
    purpose: str,
    content: str,
    input_schema: SkillSchemaPayload,
    output_schema: SkillSchemaPayload,
    usage_example: str | None,
    required_tools: list[str],
    risk_level: str,
    version: str,
    evidence_urls: list[str],
    source_summary: str | None,
) -> AgentSubmittedSkillDetailsPayload:
    """Build persistent details for a self-acquired agent skill candidate.

    Args:
        title: Candidate title.
        purpose: Candidate purpose statement.
        content: Candidate Markdown content.
        input_schema: Expected input data shape.
        output_schema: Expected output data shape.
        usage_example: Example run.
        required_tools: Required tools list.
        risk_level: Risk classification.
        version: Version string.
        evidence_urls: Research or source URLs gathered by the agent.
        source_summary: Optional summary of how the candidate was produced.

    Returns:
        AgentSubmittedSkillDetailsPayload: Persistent self-acquisition details.
    """
    harness = run_skill_candidate_harness(
        title=title,
        purpose=purpose,
        content=content,
        evidence_urls=evidence_urls,
    )
    quality_gate = run_library_quality_gate(
        item_type=ItemType.SKILL,
        title=title,
        content=content,
        evidence_urls=evidence_urls,
        source_summary=source_summary,
    )
    details = AgentSubmittedSkillDetailsPayload(
        purpose=purpose,
        input_schema=input_schema,
        output_schema=output_schema,
        usage_example=usage_example,
        required_tools=required_tools,
        risk_level=risk_level,
        version=version,
        evidence_urls=list(evidence_urls),
        source_summary=source_summary,
        acquisition_method=SkillAcquisitionMethod.SELF_ACQUISITION.value,
        harness=harness.to_payload(),
        quality_gate=quality_gate.to_payload(),
    )
    return details


def build_librarian_skill_item_payload(
    generated: CreateSkillCandidateResult,
    category_id: str | None,
    tags: list[str],
    created_by_name: str,
) -> LibrarianSkillItemPayload:
    """Build item payload fields for a librarian-generated skill candidate.

    Args:
        generated: Candidate payload from provider adapter.
        category_id: Optional category id.
        tags: Skill tags.
        created_by_name: Source display name.

    Returns:
        Payload fields owned by generated candidate normalization.
    """
    item_payload: LibrarianSkillItemPayload = {
        "title": generated.title,
        "summary": generated.summary,
        "content": generated.content,
        "category_id": category_id,
        "tags": tags,
        "details": {
            "purpose": generated.purpose,
            "input_schema": generated.input_schema,
            "output_schema": generated.output_schema,
            "usage_example": None,
            "required_tools": generated.required_tools,
            "risk_level": generated.risk_level.value,
            "version": generated.version,
            "librarian_provider_id": generated.provider_id,
            "prompt": generated.prompt,
            "quality_gate": run_library_quality_gate(
                item_type=ItemType.SKILL,
                title=generated.title,
                content=generated.content,
                evidence_urls=[],
                source_summary=generated.summary,
            ).to_payload(),
        },
    }
    return item_payload


def shape_skill_patch_payload(
    item: LibraryItemPayload,
    payload: Mapping[str, JSONValue],
) -> SkillItemUpdatePayload:
    """Shape public skill patch fields into item-service update payload.

    Args:
        item: Existing item payload.
        payload: Public skill patch payload.

    Returns:
        Item-service update payload.

    Raises:
        LibraryValidationError: When no supported fields are provided.
    """
    shaped_payload = SkillItemUpdatePayload()
    if "title" in payload:
        shaped_payload["title"] = required_string_value(payload["title"], "title")
    if "summary" in payload:
        shaped_payload["summary"] = optional_string_value(payload["summary"])
    if "content" in payload:
        shaped_payload["content"] = required_string_value(payload["content"], "content")
    if "category_id" in payload:
        shaped_payload["category_id"] = optional_string_value(payload["category_id"])
    if "tags" in payload:
        shaped_payload["tags"] = string_items(payload["tags"])
    if "status" in payload:
        shaped_payload["status"] = enum_value(payload["status"], ItemStatus, "status")

    if any(field.value in payload for field in SkillDetailField):
        details = item["details"].copy()
        for field in SkillDetailField:
            key = field.value
            if key in payload:
                details[key] = payload[key]
        shaped_payload["details"] = _skill_details_patch_payload(details)

    if not shaped_payload:
        raise LibraryValidationError("No fields provided")

    return shaped_payload
