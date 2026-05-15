"""Handlers for prompt CLI commands."""

from __future__ import annotations

from difflib import unified_diff

from app.cli_support.contracts.command_contracts import (
    ItemIdCommand,
    PromptDeprecateCommand,
    PromptDiffCommand,
    PromptsCreateCommand,
    PromptsListCommand,
    PromptsSearchCommand,
    PromptsUseCommand,
    PromptVersionCommand,
)
from app.cli_support.contracts.request_mappers import (
    prompt_create_payload,
    prompt_usage_payload,
)
from app.cli_support.contracts.runtime_contracts import CommandContext
from app.cli_support.input.argument_values import bounded_limit
from app.cli_support.presentation.output_renderers import (
    detail_text,
    json_list,
    list_field,
    print_json,
    print_prompt_table,
    text_field,
)
from app.cli_support.routing.url_paths import quote_path
from app.cli_support.schemas.prompt_command_schemas import PromptUsageResult
from app.cli_support.serialization.json_payloads import schema_payload
from app.cli_support.transport.backend_api_client import CliBackendApiClient
from app.shared.types.extra_types import JSONObject, JSONValue


def handle_prompts_list(
    command: PromptsListCommand,
    context: CommandContext,
    client: CliBackendApiClient,
) -> int:
    """Run the prompts list CLI command.

    Args:
        command: Typed CLI command contract for the operation.
        context: CLI runtime context with output settings.
        client: Backend API client used for HTTP requests.

    Returns:
        Process-style exit code.
    """
    limit = bounded_limit(command.limit, default=20)
    offset = max(0, int(command.offset))
    payload = client.get(f"/library/prompts?limit={limit}&offset={offset}")
    rows = json_list(payload)
    if command.kind is not None:
        rows = [
            row for row in rows if detail_text(row, "prompt_kind") == command.kind.value
        ]
    if command.tag is not None:
        rows = [row for row in rows if command.tag in list_field(row, "tags")]
    output_payload: JSONValue = rows
    if context.json_output:
        print_json(output_payload, context.stdout)
    else:
        print_prompt_table(output_payload, context.stdout)
    return 0


def handle_prompts_get(
    command: ItemIdCommand,
    context: CommandContext,
    client: CliBackendApiClient,
) -> int:
    """Run the prompts get CLI command.

    Args:
        command: Typed CLI command contract for the operation.
        context: CLI runtime context with output settings.
        client: Backend API client used for HTTP requests.

    Returns:
        Process-style exit code.
    """
    item_id = str(command.item_id)
    payload = client.get(f"/library/prompts/{quote_path(item_id)}")
    print_json(payload, context.stdout)
    return 0


def handle_prompts_search(
    command: PromptsSearchCommand,
    context: CommandContext,
    client: CliBackendApiClient,
) -> int:
    """Run the prompts search CLI command.

    Args:
        command: Typed CLI command contract for search.
        context: CLI runtime context with output settings.
        client: Backend API client used for HTTP requests.

    Returns:
        Process-style exit code.
    """
    limit = bounded_limit(command.limit, default=20)
    offset = max(0, int(command.offset))
    query = quote_path(command.query)
    payload = client.get(
        f"/library/items?limit={limit}&offset={offset}&item_type=PROMPT&q={query}"
    )
    rows = json_list(payload)
    if context.json_output:
        print_json(rows, context.stdout)
    else:
        print_prompt_table(rows, context.stdout)
    return 0


def handle_prompts_version(
    command: PromptVersionCommand,
    context: CommandContext,
    client: CliBackendApiClient,
) -> int:
    """Run the prompts version CLI command.

    Args:
        command: Typed CLI command contract for version updates.
        context: CLI runtime context with output settings.
        client: Backend API client used for HTTP requests.

    Returns:
        Process-style exit code.
    """
    body: JSONObject = {"version": command.version}
    if command.change_summary is not None:
        body["change_summary"] = command.change_summary
    payload = client.patch(f"/library/prompts/{quote_path(command.item_id)}", body)
    if context.json_output:
        print_json(payload, context.stdout)
    else:
        print(
            f"versioned prompt {command.item_id}: {command.version}",
            file=context.stdout,
        )
    return 0


def handle_prompts_deprecate(
    command: PromptDeprecateCommand,
    context: CommandContext,
    client: CliBackendApiClient,
) -> int:
    """Run the prompts deprecate CLI command.

    Args:
        command: Typed CLI command contract for deprecation.
        context: CLI runtime context with output settings.
        client: Backend API client used for HTTP requests.

    Returns:
        Process-style exit code.
    """
    body: JSONObject = {"status": "DEPRECATED"}
    if command.reason is not None:
        body["change_summary"] = command.reason
    payload = client.patch(f"/library/prompts/{quote_path(command.item_id)}", body)
    if context.json_output:
        print_json(payload, context.stdout)
    else:
        print(f"deprecated prompt {command.item_id}", file=context.stdout)
    return 0


def handle_prompts_diff(
    command: PromptDiffCommand,
    context: CommandContext,
    client: CliBackendApiClient,
) -> int:
    """Run the prompts diff CLI command.

    Args:
        command: Typed CLI command contract for prompt diffing.
        context: CLI runtime context with output settings.
        client: Backend API client used for HTTP requests.

    Returns:
        Process-style exit code.
    """
    left = client.get(f"/library/prompts/{quote_path(command.left_item_id)}")
    right = client.get(f"/library/prompts/{quote_path(command.right_item_id)}")
    if context.json_output:
        print_json(
            {"left": left, "right": right, "diff": _prompt_diff(left, right)},
            context.stdout,
        )
    else:
        print(_prompt_diff(left, right), file=context.stdout)
    return 0


def handle_prompts_create(
    command: PromptsCreateCommand,
    context: CommandContext,
    client: CliBackendApiClient,
) -> int:
    """Run the prompts create CLI command.

    Args:
        command: Typed CLI command contract for the operation.
        context: CLI runtime context with output settings.
        client: Backend API client used for HTTP requests.

    Returns:
        Process-style exit code.
    """
    body = prompt_create_payload(command)
    payload = client.post("/library/prompts", body)
    if context.json_output:
        print_json(payload, context.stdout)
    else:
        title = text_field(payload, "title")
        item_id = text_field(payload, "id")
        print(f"created prompt {item_id}: {title}", file=context.stdout)
    return 0


def _prompt_diff(left: JSONValue, right: JSONValue) -> str:
    left_content = text_field(left, "content").splitlines(keepends=True)
    right_content = text_field(right, "content").splitlines(keepends=True)
    diff = unified_diff(left_content, right_content, fromfile="left", tofile="right")
    return "".join(diff)


def handle_prompts_use(
    command: PromptsUseCommand,
    context: CommandContext,
    client: CliBackendApiClient,
) -> int:
    """Run the prompts use CLI command.

    Args:
        command: Typed CLI command contract for the operation.
        context: CLI runtime context with output settings.
        client: Backend API client used for HTTP requests.

    Returns:
        Process-style exit code.
    """
    item_id = str(command.item_id)
    payload = client.get(f"/library/prompts/{quote_path(item_id)}")
    usage_payload = prompt_usage_payload(command)
    usage = client.post("/library/usage", usage_payload)
    if context.json_output:
        result = PromptUsageResult(prompt=payload, usage=usage)
        print_json(schema_payload(result), context.stdout)
    else:
        print(text_field(payload, "content"), file=context.stdout)
    return 0
