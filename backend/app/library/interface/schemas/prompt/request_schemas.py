"""Request schemas for prompt-specific endpoints."""

from __future__ import annotations

from app.library.domain.event_enum.item_enums import (
    CreatedByType,
    ItemStatus,
    SourceType,
)
from app.library.domain.event_enum.prompt_enums import (
    PromptContentFormat,
    PromptDomain,
    PromptKind,
    PromptTaskType,
)
from app.shared.schemas.common_schemas import StrictSchemaModel
from pydantic import ConfigDict, Field, field_validator, model_validator


# Broad type justified: Pydantic before validators receive raw boundary input.
def _enum_value(value: object, enum_type: type) -> object:
    if isinstance(value, enum_type):
        return value
    if isinstance(value, str):
        return enum_type(value)
    raise ValueError("invalid enum value")


class PromptVariableRequest(StrictSchemaModel):
    """Template variable accepted by prompt create/update endpoints."""

    name: str = Field(min_length=1)
    required: bool = True
    description: str | None = None
    default_value: str | None = None
    example: str | None = None
    input_type: str = "text"


class PromptCreateRequest(StrictSchemaModel):
    """Payload for direct or actor-submitted prompt creation."""

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "title": "FastAPI review prompt",
                    "summary": "Review backend API changes.",
                    "content": "Review this diff: {{diff}}",
                    "content_format": "MARKDOWN",
                    "prompt_kind": "USER_TEMPLATE",
                    "prompt_domain": "DEVELOPMENT",
                    "prompt_task_type": "CODE_REVIEW",
                    "input_variables": [{"name": "diff", "required": True}],
                    "created_by_name": "alex",
                    "created_by_type": "USER",
                    "source_type": "USER_CREATED",
                    "status": "DRAFT",
                }
            ]
        }
    )

    title: str = Field(min_length=1)
    summary: str | None = None
    content: str = Field(min_length=1)
    category_id: str | None = None
    tags: list[str] = Field(default_factory=list)
    content_format: PromptContentFormat = PromptContentFormat.MARKDOWN
    prompt_kind: PromptKind = PromptKind.USER_TEMPLATE
    prompt_domain: PromptDomain = PromptDomain.GENERAL
    prompt_task_type: PromptTaskType = PromptTaskType.GENERAL_TASK
    input_variables: list[PromptVariableRequest] = Field(default_factory=list)
    output_format: str | None = None
    target_actor: str | None = None
    target_model_family: str | None = None
    language: str | None = None
    related_item_ids: list[str] = Field(default_factory=list)
    safety_notes: str | None = None
    version: str = "1.0.0"
    change_summary: str | None = None
    created_by_name: str = "Hermes User"
    created_by_type: CreatedByType = CreatedByType.USER
    source_type: SourceType = SourceType.USER_CREATED
    status: ItemStatus = ItemStatus.DRAFT

    @field_validator("content_format", mode="before")
    @classmethod
    # Broad type justified: Pydantic before validators receive raw boundary input before contract validation.
    def parse_content_format(cls, value: object) -> PromptContentFormat:
        return _enum_value(value, PromptContentFormat)  # type: ignore[return-value]

    @field_validator("prompt_kind", mode="before")
    @classmethod
    # Broad type justified: Pydantic before validators receive raw boundary input before contract validation.
    def parse_prompt_kind(cls, value: object) -> PromptKind:
        return _enum_value(value, PromptKind)  # type: ignore[return-value]

    @field_validator("prompt_domain", mode="before")
    @classmethod
    # Broad type justified: Pydantic before validators receive raw boundary input before contract validation.
    def parse_prompt_domain(cls, value: object) -> PromptDomain:
        return _enum_value(value, PromptDomain)  # type: ignore[return-value]

    @field_validator("prompt_task_type", mode="before")
    @classmethod
    # Broad type justified: Pydantic before validators receive raw boundary input before contract validation.
    def parse_prompt_task_type(cls, value: object) -> PromptTaskType:
        return _enum_value(value, PromptTaskType)  # type: ignore[return-value]

    @field_validator("created_by_type", mode="before")
    @classmethod
    # Broad type justified: Pydantic before validators receive raw boundary input before contract validation.
    def parse_created_by_type(cls, value: object) -> CreatedByType:
        return _enum_value(value, CreatedByType)  # type: ignore[return-value]

    @field_validator("source_type", mode="before")
    @classmethod
    # Broad type justified: Pydantic before validators receive raw boundary input before contract validation.
    def parse_source_type(cls, value: object) -> SourceType:
        return _enum_value(value, SourceType)  # type: ignore[return-value]

    @field_validator("status", mode="before")
    @classmethod
    # Broad type justified: Pydantic before validators receive raw boundary input before contract validation.
    def parse_status(cls, value: object) -> ItemStatus:
        return _enum_value(value, ItemStatus)  # type: ignore[return-value]

    @model_validator(mode="after")
    def unique_variables(self) -> PromptCreateRequest:
        names = [item.name for item in self.input_variables]
        if len(set(names)) != len(names):
            raise ValueError("input variable names must be unique")
        return self


class PromptPatchRequest(StrictSchemaModel):
    """Patch payload for editing an existing prompt."""

    title: str | None = None
    summary: str | None = None
    content: str | None = None
    category_id: str | None = None
    tags: list[str] | None = None
    status: ItemStatus | None = None
    content_format: PromptContentFormat | None = None
    prompt_kind: PromptKind | None = None
    prompt_domain: PromptDomain | None = None
    prompt_task_type: PromptTaskType | None = None
    input_variables: list[PromptVariableRequest] | None = None
    output_format: str | None = None
    target_actor: str | None = None
    target_model_family: str | None = None
    language: str | None = None
    related_item_ids: list[str] | None = None
    safety_notes: str | None = None
    version: str | None = None
    change_summary: str | None = None

    @field_validator("status", mode="before")
    @classmethod
    # Broad type justified: Pydantic before validators receive raw boundary input before contract validation.
    def parse_status(cls, value: object) -> ItemStatus | None:
        if value is None:
            return None
        return _enum_value(value, ItemStatus)  # type: ignore[return-value]

    @field_validator("content_format", mode="before")
    @classmethod
    # Broad type justified: Pydantic before validators receive raw boundary input before contract validation.
    def parse_content_format(cls, value: object) -> PromptContentFormat | None:
        if value is None:
            return None
        return _enum_value(value, PromptContentFormat)  # type: ignore[return-value]

    @field_validator("prompt_kind", mode="before")
    @classmethod
    # Broad type justified: Pydantic before validators receive raw boundary input before contract validation.
    def parse_prompt_kind(cls, value: object) -> PromptKind | None:
        if value is None:
            return None
        return _enum_value(value, PromptKind)  # type: ignore[return-value]

    @field_validator("prompt_domain", mode="before")
    @classmethod
    # Broad type justified: Pydantic before validators receive raw boundary input before contract validation.
    def parse_prompt_domain(cls, value: object) -> PromptDomain | None:
        if value is None:
            return None
        return _enum_value(value, PromptDomain)  # type: ignore[return-value]

    @field_validator("prompt_task_type", mode="before")
    @classmethod
    # Broad type justified: Pydantic before validators receive raw boundary input before contract validation.
    def parse_prompt_task_type(cls, value: object) -> PromptTaskType | None:
        if value is None:
            return None
        return _enum_value(value, PromptTaskType)  # type: ignore[return-value]

    @model_validator(mode="after")
    def unique_variables(self) -> PromptPatchRequest:
        if self.input_variables is None:
            return self
        names = [item.name for item in self.input_variables]
        if len(set(names)) != len(names):
            raise ValueError("input variable names must be unique")
        return self
