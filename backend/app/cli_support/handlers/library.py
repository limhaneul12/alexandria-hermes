"""Handlers for backend health CLI commands."""

from __future__ import annotations

from app.cli_support.backend_api_client import CliBackendApiClient
from app.cli_support.contracts.runtime_contracts import CommandContext
from app.cli_support.presentation.output_renderers import print_json


def handle_health(context: CommandContext, client: CliBackendApiClient) -> int:
    """Run the health CLI command.

    Args:
        context: CLI runtime context with output settings.
        client: Backend API client used for HTTP requests.

    Returns:
        Process-style exit code.
    """
    payload = client.get("/health/live")
    if context.json_output:
        print_json(payload, context.stdout)
    else:
        print("Hermes backend is reachable", file=context.stdout)
    return 0
