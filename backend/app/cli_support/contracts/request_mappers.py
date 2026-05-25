"""CLI command-to-request contract mappers."""

from __future__ import annotations

from app.cli_support.argument_values import bounded_limit, optional_text
from app.cli_support.contracts.memory_command_contracts import ContextRecallCommand
from app.memory.interface.schemas.context.context_schema import ContextSearchRequest
from app.shared.serialization.model_codec import schema_payload
from app.shared.types.extra_types import JSONObject


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
