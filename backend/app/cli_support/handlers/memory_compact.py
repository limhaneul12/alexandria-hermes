"""Handlers for Memory Compact CLI commands."""

from __future__ import annotations

from urllib.parse import urlencode

from app.cli_support.argument_values import bounded_limit
from app.cli_support.backend_api_client import CliBackendApiClient
from app.cli_support.contracts.memory_command_contracts import (
    MemoryCompactIdCommand,
    MemoryCompactListCommand,
)
from app.cli_support.contracts.runtime_contracts import CommandContext
from app.cli_support.presentation.output_renderers import (
    json_list,
    print_json,
    text_field,
)
from app.cli_support.schemas.list_filter_schemas import MemoryCompactListQuery
from app.cli_support.url_paths import quote_path
from app.shared.serialization.model_codec import schema_payload
from app.shared.types.extra_types import JSONValue


def handle_memory_compact_list(
    command: MemoryCompactListCommand,
    context: CommandContext,
    client: CliBackendApiClient,
) -> int:
    """Run the Memory Compacts list CLI command.

    Args:
        command: Typed command contract for list filters.
        context: CLI runtime context with output settings.
        client: Backend API client used for HTTP requests.

    Returns:
        Process-style exit code.
    """
    query = schema_payload(
        MemoryCompactListQuery(
            limit=bounded_limit(command.limit, default=20),
            offset=max(0, int(command.offset)),
            project=command.project,
            status=command.status.value if command.status else None,
        ),
        exclude_none=True,
    )
    payload = client.get(f"/memory/compacts?{urlencode(query)}")
    _print_memory_compact_list(payload, context)
    return 0


def handle_memory_compact_current(
    command: MemoryCompactListCommand,
    context: CommandContext,
    client: CliBackendApiClient,
) -> int:
    """Run the Memory Compacts current CLI command.

    Args:
        command: Typed command contract with the optional project filter.
        context: CLI runtime context with output settings.
        client: Backend API client used for HTTP requests.

    Returns:
        Process-style exit code.
    """
    query = (
        "" if command.project is None else f"?{urlencode({'project': command.project})}"
    )
    payload = client.get(f"/memory/compacts/current{query}")
    _print_memory_compact(payload, context)
    return 0


def handle_memory_compact_get(
    command: MemoryCompactIdCommand,
    context: CommandContext,
    client: CliBackendApiClient,
) -> int:
    """Run the Memory Compacts get CLI command.

    Args:
        command: Typed command contract with the selected compact id.
        context: CLI runtime context with output settings.
        client: Backend API client used for HTTP requests.

    Returns:
        Process-style exit code.
    """
    compact_id = str(command.compact_id)
    payload = client.get(f"/memory/compacts/{quote_path(compact_id)}")
    _print_memory_compact(payload, context)
    return 0


def _print_memory_compact_list(payload: JSONValue, context: CommandContext) -> None:
    if context.json_output:
        print_json(payload, context.stdout)
        return
    rows = json_list(payload)
    if len(rows) == 0:
        print("No Memory Compacts found.", file=context.stdout)
        return
    print("ID\tSTATUS\tPROJECT\tCOVERED_TO", file=context.stdout)
    for item in rows:
        project = text_field(item, "project") or "-"
        print(
            "\t".join(
                [
                    text_field(item, "id"),
                    text_field(item, "status"),
                    project,
                    text_field(item, "covered_to"),
                ]
            ),
            file=context.stdout,
        )


def _print_memory_compact(payload: JSONValue, context: CommandContext) -> None:
    if context.json_output:
        print_json(payload, context.stdout)
        return
    if isinstance(payload, dict):
        compact_id = text_field(payload, "id")
        status = text_field(payload, "status")
        project = text_field(payload, "project") or "-"
        print(f"{status} {compact_id} {project}", file=context.stdout)
        return
    print_json(payload, context.stdout)
