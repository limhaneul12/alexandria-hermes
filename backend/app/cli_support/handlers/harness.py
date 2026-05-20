"""Handlers for execution harness CLI commands."""

from __future__ import annotations

from urllib.parse import urlencode

from app.cli_support.argument_values import bounded_limit
from app.cli_support.backend_api_client import CliBackendApiClient
from app.cli_support.contracts.memory_command_contracts import (
    ContextIdCommand,
    HarnessCaptureCommand,
    HarnessListCommand,
)
from app.cli_support.contracts.request_mappers import harness_capture_payload
from app.cli_support.contracts.runtime_contracts import CommandContext
from app.cli_support.presentation.output_renderers import print_context_payload
from app.cli_support.url_paths import quote_path


def handle_harness_list(
    command: HarnessListCommand,
    context: CommandContext,
    client: CliBackendApiClient,
) -> int:
    """Run the harness list CLI command.

    Args:
        command: Typed CLI command contract for harness listing.
        context: CLI runtime context with output settings.
        client: Backend API client used for HTTP requests.

    Returns:
        Process-style exit code.
    """
    query = _harness_list_query(command)
    payload = client.get(f"/memory/contexts/harnesses?{query}")
    print_context_payload(payload, context)
    return 0


def handle_harness_get(
    command: ContextIdCommand,
    context: CommandContext,
    client: CliBackendApiClient,
) -> int:
    """Run the harness get CLI command.

    Args:
        command: Typed CLI command contract for one harness.
        context: CLI runtime context with output settings.
        client: Backend API client used for HTTP requests.

    Returns:
        Process-style exit code.
    """
    payload = client.get(f"/memory/contexts/harnesses/{quote_path(command.context_id)}")
    print_context_payload(payload, context)
    return 0


def handle_harness_capture(
    command: HarnessCaptureCommand,
    context: CommandContext,
    client: CliBackendApiClient,
) -> int:
    """Run the harness capture CLI command.

    Args:
        command: Typed CLI command contract for harness capture.
        context: CLI runtime context with output settings.
        client: Backend API client used for HTTP requests.

    Returns:
        Process-style exit code.
    """
    payload = client.post(
        "/memory/contexts/harnesses/capture",
        harness_capture_payload(command),
    )
    print_context_payload(payload, context)
    return 0


def handle_harness_check(
    command: HarnessCaptureCommand,
    context: CommandContext,
    client: CliBackendApiClient,
) -> int:
    """Run the harness check CLI command.

    Args:
        command: Typed CLI command contract for harness validation.
        context: CLI runtime context with output settings.
        client: Backend API client used for HTTP requests.

    Returns:
        Process-style exit code.
    """
    payload = client.post(
        "/memory/contexts/harnesses/check",
        harness_capture_payload(command),
    )
    print_context_payload(payload, context)
    return 0


def handle_harness_archive(
    command: ContextIdCommand,
    context: CommandContext,
    client: CliBackendApiClient,
) -> int:
    """Run the harness archive CLI command.

    Args:
        command: Typed CLI command contract for one harness.
        context: CLI runtime context with output settings.
        client: Backend API client used for HTTP requests.

    Returns:
        Process-style exit code.
    """
    payload = client.post(
        f"/memory/contexts/harnesses/{quote_path(command.context_id)}/archive",
        {},
    )
    print_context_payload(payload, context)
    return 0


def _harness_list_query(command: HarnessListCommand) -> str:
    params: dict[str, str] = {
        "limit": str(bounded_limit(command.limit, default=50)),
        "offset": str(max(command.offset, 0)),
        "include_archived": str(command.include_archived).lower(),
    }
    if command.project is not None:
        params["project"] = command.project
    if command.scope is not None:
        params["scope"] = command.scope.value
    if command.source_agent is not None:
        params["source_agent"] = command.source_agent
    if command.tag is not None:
        params["tag"] = command.tag
    return urlencode(params)
