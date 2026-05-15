"""Handlers for Context Vault CLI commands."""

from __future__ import annotations

from app.cli_support.contracts.command_contracts import (
    ContextIdCommand,
    ContextLintCommand,
    ContextRecallCommand,
    ContextSaveCommand,
    NoArgsCommand,
)
from app.cli_support.contracts.request_mappers import (
    content_or_file,
    context_base_payload,
    context_search_payload,
    read_content_source,
)
from app.cli_support.contracts.runtime_contracts import CommandContext
from app.cli_support.presentation.output_renderers import print_context_payload
from app.cli_support.routing.url_paths import quote_path
from app.cli_support.schemas.context_command_schemas import (
    LocalContextCommandStatus,
    UnsupportedContextOperationResult,
)
from app.cli_support.serialization.json_payloads import schema_payload
from app.cli_support.transport.backend_api_client import CliBackendApiClient


def handle_context_lint(
    command: ContextLintCommand,
    context: CommandContext,
    client: CliBackendApiClient,
) -> int:
    """Run the context lint CLI command.

    Args:
        command: Typed CLI command contract for the operation.
        context: CLI runtime context with output settings.
        client: Backend API client used for HTTP requests.

    Returns:
        Process-style exit code.
    """
    body = context_base_payload(
        command=command,
        content=read_content_source(str(command.content_file)),
    )
    payload = client.post("/library/contexts/lint", body)
    print_context_payload(payload, context)
    return 0


def handle_context_save(
    command: ContextSaveCommand,
    context: CommandContext,
    client: CliBackendApiClient,
) -> int:
    """Run the context save CLI command.

    Args:
        command: Typed CLI command contract for the operation.
        context: CLI runtime context with output settings.
        client: Backend API client used for HTTP requests.

    Returns:
        Process-style exit code.
    """
    body = context_base_payload(
        command=command,
        content=content_or_file(command.content, command.content_file, "context"),
    )
    payload = client.post("/library/contexts", body)
    print_context_payload(payload, context)
    return 0


def handle_context_recall(
    command: ContextRecallCommand,
    context: CommandContext,
    client: CliBackendApiClient,
) -> int:
    """Run the context recall CLI command.

    Args:
        command: Typed CLI command contract for the operation.
        context: CLI runtime context with output settings.
        client: Backend API client used for HTTP requests.

    Returns:
        Process-style exit code.
    """
    body = context_search_payload(command)
    payload = client.post("/library/contexts/search", body)
    print_context_payload(payload, context)
    return 0


def handle_context_chunks(
    command: ContextIdCommand,
    context: CommandContext,
    client: CliBackendApiClient,
) -> int:
    """Run the context chunks CLI command.

    Args:
        command: Typed CLI command contract for the operation.
        context: CLI runtime context with output settings.
        client: Backend API client used for HTTP requests.

    Returns:
        Process-style exit code.
    """
    context_id = str(command.context_id)
    payload = client.get(f"/library/contexts/{quote_path(context_id)}/chunks")
    print_context_payload(payload, context)
    return 0


def handle_context_embed(
    command: ContextIdCommand,
    context: CommandContext,
) -> int:
    """Run the context embed CLI command.

    Args:
        command: Typed CLI command contract for the operation.
        context: CLI runtime context with output settings.

    Returns:
        Process-style exit code.
    """
    result = UnsupportedContextOperationResult(
        context_id=command.context_id,
        status=LocalContextCommandStatus.NOT_AVAILABLE,
        reason="Backend embedding jobs are not exposed as a write API in this MVP.",
    )
    payload = schema_payload(result, exclude_none=True)
    print_context_payload(payload, context)
    return 0


def handle_context_reindex(
    command: NoArgsCommand,
    context: CommandContext,
) -> int:
    """Run the context reindex CLI command.

    Args:
        command: Typed CLI command contract for the operation.
        context: CLI runtime context with output settings.

    Returns:
        Process-style exit code.
    """
    result = UnsupportedContextOperationResult(
        status=LocalContextCommandStatus.NOT_AVAILABLE,
        reason="Context FTS rows are synchronized on save/archive in this MVP.",
    )
    payload = schema_payload(result, exclude_none=True)
    print_context_payload(payload, context)
    return 0


def handle_context_doctor_rag(
    context: CommandContext,
    client: CliBackendApiClient,
) -> int:
    """Run the context doctor rag CLI command.

    Args:
        context: CLI runtime context with output settings.
        client: Backend API client used for HTTP requests.

    Returns:
        Process-style exit code.
    """
    payload = client.get("/library/contexts/rag/status")
    print_context_payload(payload, context)
    return 0
