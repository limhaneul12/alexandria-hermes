"""Prompt domain payload contracts."""

from __future__ import annotations

from app.library.domain.event_enum.item_enums import ItemStatus
from app.shared.types.extra_types import JSONObject
from typing_extensions import TypedDict


class PromptVariablePayload(TypedDict, total=False, closed=True):
    """One template variable in a reusable prompt."""

    name: str
    required: bool
    description: str | None
    default_value: str | None
    example: str | None
    input_type: str


class PromptDetailsPayload(TypedDict, closed=True):
    """Persistent details object for a prompt library item."""

    content_format: str
    prompt_kind: str
    prompt_domain: str
    prompt_task_type: str
    input_variables: list[PromptVariablePayload]
    output_format: str | None
    target_actor: str | None
    target_model_family: str | None
    language: str | None
    related_item_ids: list[str]
    safety_notes: str | None
    version: str
    change_summary: str | None
    quality_gate: JSONObject


class PromptDetailsPatchPayload(TypedDict, total=False, closed=True):
    """Merged prompt details payload for item patch operations."""

    content_format: str
    prompt_kind: str
    prompt_domain: str
    prompt_task_type: str
    input_variables: list[PromptVariablePayload]
    output_format: str | None
    target_actor: str | None
    target_model_family: str | None
    language: str | None
    related_item_ids: list[str]
    safety_notes: str | None
    version: str
    change_summary: str | None
    quality_gate: JSONObject


class PromptPatchPayload(TypedDict, total=False, closed=True):
    """Public prompt patch payload supported by prompt update flows."""

    title: str
    summary: str | None
    content: str
    category_id: str | None
    tags: list[str]
    status: ItemStatus
    content_format: str
    prompt_kind: str
    prompt_domain: str
    prompt_task_type: str
    input_variables: list[PromptVariablePayload]
    output_format: str | None
    target_actor: str | None
    target_model_family: str | None
    language: str | None
    related_item_ids: list[str]
    safety_notes: str | None
    version: str
    change_summary: str | None


class PromptItemUpdatePayload(TypedDict, total=False, closed=True):
    """Item-service update payload produced from public prompt patch fields."""

    title: str
    summary: str | None
    content: str
    category_id: str | None
    tags: list[str]
    status: ItemStatus
    details: PromptDetailsPatchPayload
