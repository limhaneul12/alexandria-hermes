"""Handlers for Context Vault CLI commands."""

from __future__ import annotations

from app.cli_support.argument_values import bounded_limit
from app.cli_support.backend_api_client import CliBackendApiClient
from app.cli_support.contracts.memory_command_contracts import (
    ContextCurateCommand,
    ContextIdCommand,
    ContextMemoryMapCommand,
    ContextRecallCommand,
    ContextReindexCommand,
)
from app.cli_support.contracts.request_mappers import (
    context_search_payload,
)
from app.cli_support.contracts.runtime_contracts import CommandContext
from app.cli_support.presentation.output_renderers import (
    print_context_payload,
)
from app.cli_support.schemas.context_command_schemas import (
    LocalContextCommandStatus,
    UnsupportedContextOperationResult,
)
from app.cli_support.url_paths import quote_path
from app.shared.serialization.model_codec import schema_payload
from app.shared.types.extra_types import JSONObject, JSONValue


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
    payload = client.post("/memory/contexts/retrieval/search", body)
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
    payload = client.get(f"/memory/contexts/{quote_path(context_id)}/chunks")
    print_context_payload(payload, context)
    return 0


def handle_context_delete(
    command: ContextIdCommand,
    context: CommandContext,
    client: CliBackendApiClient,
) -> int:
    """Run the context hard-delete CLI command.

    Args:
        command: Typed CLI command contract for the operation.
        context: CLI runtime context with output settings.
        client: Backend API client used for HTTP requests.

    Returns:
        Process-style exit code.
    """
    context_id = str(command.context_id)
    client.delete(f"/memory/contexts/{quote_path(context_id)}")
    if context.json_output:
        print_context_payload({"deleted": True, "context_id": context_id}, context)
        return 0
    print(f"deleted context {context_id}", file=context.stdout)
    return 0


def handle_context_memory_map(
    command: ContextMemoryMapCommand,
    context: CommandContext,
    client: CliBackendApiClient,
) -> int:
    """Run the context memory-map CLI command.

    Args:
        command: Typed CLI command contract for memory-map generation.
        context: CLI runtime context with output settings.
        client: Backend API client used for HTTP requests.

    Returns:
        Process-style exit code.
    """
    limit = bounded_limit(command.limit, default=10)
    query = (
        f"limit={limit}&offset=0&include_archived="
        f"{str(command.include_archived).lower()}"
    )
    if command.project is not None:
        query = f"{query}&project={quote_path(command.project)}"
    payload = client.get(f"/memory/contexts?{query}")
    result = _memory_map_payload(payload)
    print_context_payload(result, context)
    return 0


def handle_context_curate(
    command: ContextCurateCommand,
    context: CommandContext,
    client: CliBackendApiClient,
) -> int:
    """Run the context curate CLI command.

    Args:
        command: Typed CLI command contract for curator candidates.
        context: CLI runtime context with output settings.
        client: Backend API client used for HTTP requests.

    Returns:
        Process-style exit code.
    """
    limit = bounded_limit(command.limit, default=50)
    query = f"limit={limit}&offset=0&include_archived=false"
    if command.project is not None:
        query = f"{query}&project={quote_path(command.project)}"
    payload = client.get(f"/memory/contexts?{query}")
    result: JSONObject = {
        "project": command.project,
        "stale_after_days": command.stale_after_days,
        "candidates": _curation_candidates(payload),
    }
    print_context_payload(result, context)
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


def _memory_map_payload(payload: JSONValue) -> JSONObject:
    if not isinstance(payload, dict):
        return {"items": [], "summary": "No context entries returned."}
    items = payload.get("items")
    if not isinstance(items, list):
        return {"items": [], "summary": "No context entries returned."}
    top_decisions = [
        item
        for item in items
        if isinstance(item, dict) and item.get("kind") in {"DECISION", "BUG_ROOT_CAUSE"}
    ][:10]
    return {
        "total": payload.get("total", len(items)),
        "important_decisions": top_decisions,
        "recent_contexts": items,
        "summary": "Project memory map built from Context Vault entries.",
    }


def _curation_candidates(payload: JSONValue) -> list[JSONValue]:
    if not isinstance(payload, dict):
        return []
    items = payload.get("items")
    if not isinstance(items, list):
        return []
    return [
        item
        for item in items
        if isinstance(item, dict)
        and (
            item.get("status") in {"SAVED_WITH_WARNINGS", "PENDING_REVIEW"}
            or item.get("is_archived") is True
        )
    ]


def handle_context_reindex(
    command: ContextReindexCommand,
    context: CommandContext,
    client: CliBackendApiClient,
) -> int:
    """Run the context reindex CLI command.

    Args:
        command: Typed CLI command contract for the operation.
        context: CLI runtime context with output settings.
        client: Backend API client used for HTTP requests.

    Returns:
        Process-style exit code.
    """
    query = f"limit={command.limit}&force={str(command.force).lower()}"
    payload = client.post(f"/memory/contexts/retrieval/reindex?{query}", {})
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
    payload = client.get("/memory/contexts/rag/status")
    print_context_payload(payload, context)
    return 0
