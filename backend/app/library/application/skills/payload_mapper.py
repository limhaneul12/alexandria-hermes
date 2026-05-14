"""Pure skill payload mapping and patch shaping."""

from __future__ import annotations

from collections.abc import Mapping
from typing import cast

from app.library.domain.contracts.librarian_candidate_contracts import (
    CreateSkillCandidateResult,
)
from app.library.domain.event_enum.item_enums import ItemStatus
from app.library.domain.types.item_payload_types import LibraryItemPayload
from app.library.domain.types.skill_payload_types import (
    LibrarianSkillItemPayload,
    SkillDetailsPatchPayload,
    SkillDetailsPayload,
    SkillItemUpdatePayload,
    SkillSchemaPayload,
)
from app.shared.exceptions import ValidationError
from app.shared.types.extra_types import JSONValue
from app.shared.types.types_convert_utils import (
    enum_value,
    json_object_value,
    optional_string_value,
    required_string_value,
    string_items,
)

_SKILL_BASE_PATCH_FIELDS = frozenset(
    {
        "title",
        "summary",
        "content",
        "category_id",
        "tags",
        "status",
    }
)
_SKILL_DETAIL_FIELDS = (
    "purpose",
    "input_schema",
    "output_schema",
    "usage_example",
    "required_tools",
    "risk_level",
    "version",
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
    payload: SkillDetailsPatchPayload = {}
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
    skill_details: SkillDetailsPayload = {
        "purpose": purpose,
        "input_schema": input_schema,
        "output_schema": output_schema,
        "usage_example": usage_example,
        "required_tools": required_tools,
        "risk_level": risk_level,
        "version": version,
    }
    return skill_details


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
        ValidationError: When no supported fields are provided.
    """
    shaped_payload: SkillItemUpdatePayload = {}
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

    if any(key in payload for key in _SKILL_DETAIL_FIELDS):
        details = item["details"].copy()
        for key in _SKILL_DETAIL_FIELDS:
            if key in payload:
                details[key] = payload[key]
        shaped_payload["details"] = _skill_details_patch_payload(details)

    if not shaped_payload:
        raise ValidationError("No fields provided")

    return shaped_payload
