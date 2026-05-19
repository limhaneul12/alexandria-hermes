"""CLI command-to-request contract mappers."""

from __future__ import annotations

import sys
from pathlib import Path

from app.cli_support.argument_values import bounded_limit, optional_text
from app.cli_support.contracts.command_contracts import (
    ContextRecallCommand,
    FoldersCreateCommand,
    PromptsUseCommand,
)
from app.cli_support.json_payloads import schema_payload
from app.library.domain.event_enum.item_enums import ItemType
from app.library.domain.event_enum.usage_enums import SelectionSource
from app.library.interface.schemas.category.category_schema import CategoryCreateRequest
from app.library.interface.schemas.usage.usage_schema import UsageRecordRequest
from app.memory.interface.schemas.context.context_schema import (
    ContextSearchRequest,
)
from app.shared.exceptions.cli_exceptions import CliInputError
from app.shared.types.extra_types import JSONObject


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
