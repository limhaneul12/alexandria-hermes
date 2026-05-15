"""CLI command-to-request contract mappers."""

from __future__ import annotations

import sys
from pathlib import Path

from app.archive.interface.schemas.minio_archive.minio_archive_schema import (
    MinioImportRequest,
)
from app.cli_support.contracts.command_contracts import (
    ContextLintCommand,
    ContextRecallCommand,
    ContextSaveCommand,
    FoldersCreateCommand,
    MinioCommand,
    PromptsCreateCommand,
    PromptsUseCommand,
    SkillsCreateCommand,
)
from app.cli_support.input.argument_values import bounded_limit, optional_text
from app.cli_support.serialization.json_payloads import schema_payload
from app.library.domain.event_enum.item_enums import ItemStatus, ItemType
from app.library.domain.event_enum.usage_enums import SelectionSource
from app.library.interface.schemas.category.category_schema import CategoryCreateRequest
from app.library.interface.schemas.prompt.request_schemas import (
    PromptCreateRequest,
    PromptVariableRequest,
)
from app.library.interface.schemas.skill.request_schemas import (
    AgentSubmitSkillRequest,
    SkillCreateRequest,
)
from app.library.interface.schemas.usage.usage_schema import UsageRecordRequest
from app.memory.interface.schemas.context.context_schema import (
    ContextLintRequest,
    ContextSaveRequest,
    ContextSearchRequest,
)
from app.shared.exceptions.cli_exceptions import CliInputError
from app.shared.types.extra_types import JSONObject


def skill_create_payload(command: SkillsCreateCommand) -> JSONObject:
    """Map a skill create command to the backend request contract.

    Args:
        command: CLI command contract for creating a skill.

    Returns:
        JSON-compatible skill create request payload.
    """
    content = skill_content(command.content, command.content_file)
    status = ItemStatus.ACTIVE if command.active else ItemStatus.DRAFT
    request = SkillCreateRequest(
        title=command.title,
        summary=optional_text(command.summary),
        content=content,
        category_id=optional_text(command.category_id),
        tags=[str(tag) for tag in command.tag],
        purpose=command.purpose,
        input_schema={},
        output_schema={},
        usage_example=optional_text(command.usage_example),
        required_tools=[str(tool) for tool in command.tool],
        risk_level=command.risk_level,
        version=command.version,
        created_by_name=command.created_by,
        status=status,
    )
    payload = schema_payload(request)
    return payload


def agent_skill_submit_payload(command: SkillsCreateCommand) -> JSONObject:
    """Map a skill create command to the agent-submit request contract.

    Args:
        command: CLI command contract for creating a skill candidate.

    Returns:
        JSON-compatible agent skill submit request payload.
    """
    content = skill_content(command.content, command.content_file)
    status = ItemStatus.ACTIVE if command.active else ItemStatus.DRAFT
    created_by_name = command.created_by
    if command.source_agent is not None:
        created_by_name = command.source_agent
    request = AgentSubmitSkillRequest(
        title=command.title,
        purpose=command.purpose,
        summary=optional_text(command.summary),
        content=content,
        category_id=optional_text(command.category_id),
        tags=[str(tag) for tag in command.tag],
        input_schema={},
        output_schema={},
        usage_example=optional_text(command.usage_example),
        required_tools=[str(tool) for tool in command.tool],
        risk_level=command.risk_level,
        version=command.version,
        created_by_name=created_by_name,
        activate=command.active,
        status=status,
        evidence_urls=[url.strip() for url in command.evidence_url if url.strip()],
        source_summary=optional_text(command.source_summary),
    )
    payload = schema_payload(request)
    return payload


def skill_content(content: str | None, content_file: str | None) -> str:
    """Read skill content from inline text, stdin, or a file.

    Args:
        content: Inline content supplied by the CLI.
        content_file: File path or '-' for stdin.

    Returns:
        Non-empty skill content.

    Raises:
        CliInputError: When no content is provided.
    """
    if content_file is not None:
        if content_file == "-":
            loaded_content = sys.stdin.read()
        else:
            loaded_content = Path(content_file).read_text(encoding="utf-8")
    elif content is not None:
        loaded_content = content
    else:
        raise CliInputError("skill content is required via --content or --content-file")
    if not loaded_content.strip():
        raise CliInputError("skill content is required via --content or --content-file")
    return loaded_content


def prompt_create_payload(command: PromptsCreateCommand) -> JSONObject:
    """Map a prompt create command to the backend request contract.

    Args:
        command: CLI command contract for creating a prompt.

    Returns:
        JSON-compatible prompt create request payload.
    """
    content = prompt_content(command.content, command.content_file)
    status = ItemStatus.ACTIVE if command.active else ItemStatus.DRAFT
    request = PromptCreateRequest(
        title=command.title,
        summary=optional_text(command.summary),
        content=content,
        category_id=optional_text(command.category_id),
        tags=[str(tag) for tag in command.tag],
        content_format=command.content_format,
        prompt_kind=command.kind,
        prompt_domain=command.domain,
        prompt_task_type=command.task_type,
        input_variables=[prompt_variable_request(raw) for raw in command.var],
        output_format=optional_text(command.output_format),
        target_actor=optional_text(command.target_actor),
        target_model_family=optional_text(command.target_model_family),
        language=optional_text(command.language),
        related_item_ids=[str(item_id) for item_id in command.related_item_id],
        safety_notes=None,
        version=command.version,
        change_summary=None,
        created_by_name=command.created_by,
        created_by_type=command.created_by_type,
        source_type=command.source_type,
        status=status,
    )
    payload = schema_payload(request)
    return payload


def prompt_usage_payload(command: PromptsUseCommand) -> JSONObject:
    """Map a prompt use command to the usage record request contract.

    Args:
        command: CLI command contract for prompt rendering.

    Returns:
        JSON-compatible usage record request payload.
    """
    request = UsageRecordRequest(
        item_id=command.item_id,
        item_type=ItemType.PROMPT.value,
        agent_name=command.actor_name,
        librarian_provider=optional_text(command.actor_id),
        query=None,
        selection_source=SelectionSource.DIRECT_LINK,
        success=True,
        feedback=None,
    )
    payload = schema_payload(request, exclude_none=True)
    return payload


def prompt_variable_request(raw_value: str) -> PromptVariableRequest:
    """Parse one CLI prompt variable into a request schema.

    Args:
        raw_value: Variable expression in name[:required|optional][:description] form.

    Returns:
        Prompt variable request schema.

    Raises:
        CliInputError: When the variable name is blank.
    """
    name, _, rest = raw_value.partition(":")
    variable_name = name.strip()
    if not variable_name:
        raise CliInputError("prompt variable name is required")
    parts = rest.split(":") if rest else []
    required = True
    description_parts: list[str] = []
    for part in parts:
        normalized = part.strip()
        if normalized == "required":
            required = True
        elif normalized == "optional":
            required = False
        elif normalized:
            description_parts.append(normalized)
    description = ":".join(description_parts)
    if description == "":
        normalized_description = None
    else:
        normalized_description = description
    request = PromptVariableRequest(
        name=variable_name,
        required=required,
        description=normalized_description,
        default_value=None,
        example=None,
        input_type="text",
    )
    return request


def prompt_content(content: str | None, content_file: str | None) -> str:
    """Read prompt content from inline text, stdin, or a file.

    Args:
        content: Inline prompt content supplied by the CLI.
        content_file: File path or '-' for stdin.

    Returns:
        Non-empty prompt content.

    Raises:
        CliInputError: When no prompt content is provided.
    """
    if content_file is not None:
        if content_file == "-":
            loaded_content = sys.stdin.read()
        else:
            loaded_content = Path(content_file).read_text(encoding="utf-8")
    elif content is not None:
        loaded_content = content
    else:
        raise CliInputError(
            "prompt content is required via --content or --content-file"
        )
    if not loaded_content.strip():
        raise CliInputError(
            "prompt content is required via --content or --content-file"
        )
    return loaded_content


def context_base_payload(
    command: ContextLintCommand | ContextSaveCommand,
    content: str,
) -> JSONObject:
    """Map context lint/save metadata to the backend request contract.

    Args:
        command: CLI context command carrying shared metadata.
        content: Normalized context Markdown content.

    Returns:
        JSON-compatible context request payload.
    """
    if isinstance(command, ContextSaveCommand):
        request = ContextSaveRequest(
            kind=command.kind,
            title=command.title,
            content=content.strip(),
            summary=optional_text(command.summary),
            project=optional_text(command.project),
            scope=command.scope,
            workspace_id=optional_text(command.workspace_id),
            agent_id=optional_text(command.agent_id),
            user_id=optional_text(command.user_id),
            session_id=optional_text(command.session_id),
            visibility=command.visibility,
            source_agent=command.source_agent,
            tags=[str(tag) for tag in command.tag],
            source_type=command.source_type,
            importance=command.importance,
            expires_at=None,
            metadata={},
        )
    else:
        request = ContextLintRequest(
            kind=command.kind,
            title=command.title,
            content=content.strip(),
            summary=optional_text(command.summary),
            project=optional_text(command.project),
            scope=command.scope,
            workspace_id=optional_text(command.workspace_id),
            agent_id=optional_text(command.agent_id),
            user_id=optional_text(command.user_id),
            session_id=optional_text(command.session_id),
            visibility=command.visibility,
            source_agent=command.source_agent,
            tags=[str(tag) for tag in command.tag],
        )
    payload = schema_payload(request)
    for key in ("workspace_id", "agent_id", "user_id", "session_id"):
        if payload.get(key) is None:
            del payload[key]
    return payload


def context_search_payload(command: ContextRecallCommand) -> JSONObject:
    """Map a context recall command to the backend search contract.

    Args:
        command: CLI command contract for context recall.

    Returns:
        JSON-compatible context search request payload.
    """
    request = ContextSearchRequest(
        query=command.query,
        strategy=command.strategy,
        limit=bounded_limit(command.limit, default=5),
        project=optional_text(command.project),
        kind=command.kind,
        include_scopes=command.include_scopes,
        workspace_id=optional_text(command.workspace_id),
        agent_id=optional_text(command.agent_id),
        user_id=optional_text(command.user_id),
        session_id=optional_text(command.session_id),
    )
    payload = schema_payload(request, exclude_none=True)
    if payload.get("include_scopes") == []:
        del payload["include_scopes"]
    return payload


def folder_create_payload(command: FoldersCreateCommand) -> JSONObject:
    """Map a folder create command to the backend category contract.

    Args:
        command: CLI command contract for category creation.

    Returns:
        JSON-compatible category create request payload.
    """
    request = CategoryCreateRequest(
        name=command.name,
        parent_id=optional_text(command.parent_id),
    )
    payload = schema_payload(request)
    return payload


def minio_import_payload(command: MinioCommand) -> JSONObject:
    """Map a MINIO import command to the backend import contract.

    Args:
        command: CLI command contract for MINIO archive import.

    Returns:
        JSON-compatible MINIO import request payload.
    """
    request = MinioImportRequest(limit=command.limit)
    payload = schema_payload(request)
    return payload


def content_or_file(
    content: str | None,
    content_file: str | None,
    content_name: str,
) -> str:
    """Read required content from inline text, stdin, or a file.

    Args:
        content: Inline content supplied by the CLI.
        content_file: File path or '-' for stdin.
        content_name: Human-readable content name for errors.

    Returns:
        Trimmed non-empty content.

    Raises:
        CliInputError: When no content is provided.
    """
    if content_file is not None:
        loaded_content = read_content_source(content_file)
    elif content is not None:
        loaded_content = content
    else:
        raise CliInputError(
            f"{content_name} content is required via --content or --content-file"
        )
    if not loaded_content.strip():
        raise CliInputError(
            f"{content_name} content is required via --content or --content-file"
        )
    return loaded_content.strip()


def read_content_source(content_file: str) -> str:
    """Read content from stdin or a filesystem path.

    Args:
        content_file: File path or '-' for stdin.

    Returns:
        Trimmed content text.
    """
    if content_file == "-":
        loaded_content = sys.stdin.read()
    else:
        loaded_content = Path(content_file).read_text(encoding="utf-8")
    return loaded_content.strip()
