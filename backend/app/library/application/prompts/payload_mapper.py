"""Pure prompt payload mapping and patch shaping."""

from __future__ import annotations

from collections.abc import Mapping
from typing import cast

from app.library.application.quality_gate import run_library_quality_gate
from app.library.domain.event_enum.item_enums import ItemStatus, ItemType
from app.library.domain.event_enum.prompt_enums import (
    PromptContentFormat,
    PromptDetailField,
    PromptDomain,
    PromptKind,
    PromptTaskType,
)
from app.library.domain.types.item_payload_types import LibraryItemPayload
from app.library.domain.types.prompt_payload_types import (
    PromptDetailsPatchPayload,
    PromptDetailsPayload,
    PromptItemUpdatePayload,
    PromptVariablePayload,
)
from app.shared.exceptions import LibraryValidationError
from app.shared.types.extra_types import JSONValue
from app.shared.types.types_convert_utils import (
    bool_value,
    enum_value,
    optional_string_value,
    required_string_value,
    string_items,
)


def _variable_payload(value: JSONValue) -> PromptVariablePayload:
    """Normalize one prompt variable payload."""
    if not isinstance(value, dict):
        raise LibraryValidationError("input_variables must contain objects")
    name = required_string_value(value.get("name"), "input_variables.name")
    variable: PromptVariablePayload = {
        "name": name,
        "required": bool_value(value.get("required"), default=True),
        "description": optional_string_value(value.get("description")),
        "default_value": optional_string_value(value.get("default_value")),
        "example": optional_string_value(value.get("example")),
        "input_type": required_string_value(
            value.get("input_type", "text"), "input_variables.input_type"
        ),
    }
    return variable


def _variables_payload(value: JSONValue) -> list[PromptVariablePayload]:
    """Normalize variable list and reject duplicates."""
    if value is None:
        return []
    if not isinstance(value, list):
        raise LibraryValidationError("input_variables must be a list")
    variables = [_variable_payload(item) for item in value]
    names = [item["name"] for item in variables]
    if len(set(names)) != len(names):
        raise LibraryValidationError("input_variables names must be unique")
    return variables


def build_prompt_details(
    title: str,
    content: str,
    content_format: PromptContentFormat,
    prompt_kind: PromptKind,
    prompt_domain: PromptDomain,
    prompt_task_type: PromptTaskType,
    input_variables: list[PromptVariablePayload],
    output_format: str | None,
    target_actor: str | None,
    target_model_family: str | None,
    language: str | None,
    related_item_ids: list[str],
    safety_notes: str | None,
    version: str,
    change_summary: str | None,
) -> PromptDetailsPayload:
    """Build persistent details for a prompt item.

    Args:
        title: Prompt title.
        content: Prompt body.
        content_format: Body syntax.
        prompt_kind: Prompt usage position.
        prompt_domain: Business domain.
        prompt_task_type: Task classification.
        input_variables: Template variables.
        output_format: Optional output guidance.
        target_actor: Optional actor.
        target_model_family: Optional model family.
        language: Optional language hint.
        related_item_ids: Related item ids.
        safety_notes: Optional safety notes.
        version: Version text.
        change_summary: Optional change summary.

    Returns:
        Persistent details dictionary.
    """
    quality_gate = run_library_quality_gate(
        item_type=ItemType.PROMPT,
        title=title,
        content=content,
    )
    details: PromptDetailsPayload = {
        "content_format": content_format.value,
        "prompt_kind": prompt_kind.value,
        "prompt_domain": prompt_domain.value,
        "prompt_task_type": prompt_task_type.value,
        "input_variables": input_variables,
        "output_format": output_format,
        "target_actor": target_actor,
        "target_model_family": target_model_family,
        "language": language,
        "related_item_ids": related_item_ids,
        "safety_notes": safety_notes,
        "version": version,
        "change_summary": change_summary,
        "quality_gate": quality_gate.to_payload(),
    }
    return details


def _prompt_details_patch_payload(
    details: Mapping[str, JSONValue],
) -> PromptDetailsPatchPayload:
    """Normalize merged item details into the prompt details patch contract."""
    payload: PromptDetailsPatchPayload = {}
    if "content_format" in details:
        payload["content_format"] = enum_value(
            details["content_format"], PromptContentFormat, "content_format"
        ).value
    if "prompt_kind" in details:
        payload["prompt_kind"] = enum_value(
            details["prompt_kind"], PromptKind, "prompt_kind"
        ).value
    if "prompt_domain" in details:
        payload["prompt_domain"] = enum_value(
            details["prompt_domain"], PromptDomain, "prompt_domain"
        ).value
    if "prompt_task_type" in details:
        payload["prompt_task_type"] = enum_value(
            details["prompt_task_type"], PromptTaskType, "prompt_task_type"
        ).value
    if "input_variables" in details:
        payload["input_variables"] = _variables_payload(details["input_variables"])
    if "output_format" in details:
        payload["output_format"] = optional_string_value(details["output_format"])
    if "target_actor" in details:
        payload["target_actor"] = optional_string_value(details["target_actor"])
    if "target_model_family" in details:
        payload["target_model_family"] = optional_string_value(
            details["target_model_family"]
        )
    if "language" in details:
        payload["language"] = optional_string_value(details["language"])
    if "related_item_ids" in details:
        payload["related_item_ids"] = string_items(details["related_item_ids"])
    if "safety_notes" in details:
        payload["safety_notes"] = optional_string_value(details["safety_notes"])
    if "version" in details:
        payload["version"] = required_string_value(details["version"], "version")
    if "change_summary" in details:
        payload["change_summary"] = optional_string_value(details["change_summary"])
    if "quality_gate" in details and isinstance(details["quality_gate"], dict):
        payload["quality_gate"] = dict(details["quality_gate"])
    return payload


def shape_prompt_patch_payload(
    item: LibraryItemPayload,
    payload: Mapping[str, JSONValue],
) -> PromptItemUpdatePayload:
    """Shape public prompt patch fields into item-service update payload.

    Args:
        item: Existing item payload.
        payload: Public prompt patch payload.

    Returns:
        Item-service update payload.

    Raises:
        LibraryValidationError: When no supported fields are provided.
    """
    shaped_payload: PromptItemUpdatePayload = {}
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
    if any(field.value in payload for field in PromptDetailField):
        details = item["details"].copy()
        for field in PromptDetailField:
            key = field.value
            if key in payload:
                details[key] = payload[key]
        shaped_payload["details"] = _prompt_details_patch_payload(
            cast(Mapping[str, JSONValue], details)
        )
    if not shaped_payload:
        raise LibraryValidationError("No fields provided")
    return shaped_payload
