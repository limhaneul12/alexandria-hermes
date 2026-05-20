"""MCP HTTP tool adapters for execution harness contexts."""

from __future__ import annotations

from urllib.parse import quote

from app.mcp_server.backend_api_client import AlexandriaApiClient
from app.memory.domain.event_enum.context_enums import ContextScope
from app.memory.interface.schemas.context.context_schema import HarnessCaptureRequest
from app.shared.serialization.model_codec import schema_payload
from app.shared.types.extra_types import JSONObject, JSONValue

DEFAULT_HARNESS_SOURCE_AGENT = "Hermes"
DEFAULT_HARNESS_LIMIT = 5


async def alexandria_capture_harness(
    client: AlexandriaApiClient,
    task_goal: str,
    reusable_procedure: str,
    summary: str | None = None,
    project: str | None = None,
    scope: ContextScope = ContextScope.PROJECT,
    workspace_id: str | None = None,
    agent_id: str | None = None,
    user_id: str | None = None,
    session_id: str | None = None,
    source_agent: str = DEFAULT_HARNESS_SOURCE_AGENT,
    environment: str | None = None,
    trigger_context: str | None = None,
    steps: list[str] | None = None,
    commands: list[str] | None = None,
    tests: list[str] | None = None,
    failures: list[str] | None = None,
    fixes: list[str] | None = None,
    artifacts: list[str] | None = None,
    recall_keywords: list[str] | None = None,
    safety_notes: list[str] | None = None,
) -> JSONValue:
    """Capture an agent-owned execution harness through Context Vault.

    Args:
        client: Backend HTTP client.
        task_goal: Goal the agent executed.
        reusable_procedure: Procedure future agents can reuse.
        summary: Optional summary.
        project: Optional project scope.
        scope: Recall-routing scope.
        workspace_id: Optional workspace identifier.
        agent_id: Optional agent identifier.
        user_id: Optional user identifier.
        session_id: Optional session identifier.
        source_agent: Producing agent name.
        environment: Optional environment description.
        trigger_context: Why this harness was created.
        steps: Ordered execution steps.
        commands: Commands that were run.
        tests: Tests or checks that were run.
        failures: Failures encountered.
        fixes: Fixes applied.
        artifacts: Relevant artifact handles.
        recall_keywords: Keywords for later recall.
        safety_notes: Safety and side-effect notes.

    Returns:
        Stored HARNESS context response.
    """
    request = HarnessCaptureRequest(
        task_goal=task_goal,
        reusable_procedure=reusable_procedure,
        summary=summary,
        project=project,
        scope=scope,
        workspace_id=workspace_id,
        agent_id=agent_id,
        user_id=user_id,
        session_id=session_id,
        source_agent=source_agent,
        environment=environment,
        trigger_context=trigger_context,
        steps=_items_or_empty(steps),
        commands=_items_or_empty(commands),
        tests=_items_or_empty(tests),
        failures=_items_or_empty(failures),
        fixes=_items_or_empty(fixes),
        artifacts=_items_or_empty(artifacts),
        recall_keywords=_items_or_empty(recall_keywords),
        safety_notes=_items_or_empty(safety_notes),
        metadata={},
    )
    payload = schema_payload(request, exclude_none=True)
    response = await client.post("/memory/contexts/harnesses/capture", payload)
    return response


async def alexandria_check_harness(
    client: AlexandriaApiClient,
    task_goal: str,
    reusable_procedure: str,
    summary: str | None = None,
    project: str | None = None,
    scope: ContextScope = ContextScope.PROJECT,
    source_agent: str = DEFAULT_HARNESS_SOURCE_AGENT,
    environment: str | None = None,
    trigger_context: str | None = None,
    steps: list[str] | None = None,
    commands: list[str] | None = None,
    tests: list[str] | None = None,
    failures: list[str] | None = None,
    fixes: list[str] | None = None,
    artifacts: list[str] | None = None,
    recall_keywords: list[str] | None = None,
    safety_notes: list[str] | None = None,
) -> JSONValue:
    """Validate an execution harness without saving it.

    Args:
        client: Backend HTTP client.
        task_goal: Goal the harness solves.
        reusable_procedure: Procedure future agents can reuse.
        summary: Optional summary.
        project: Optional project scope.
        scope: Recall-routing scope.
        source_agent: Producing agent name.
        environment: Optional environment description.
        trigger_context: Why this harness was created.
        steps: Ordered execution steps.
        commands: Commands that were run.
        tests: Tests or checks that were run.
        failures: Failures encountered.
        fixes: Fixes applied.
        artifacts: Relevant artifact handles.
        recall_keywords: Keywords for later recall.
        safety_notes: Safety and side-effect notes.

    Returns:
        Harness lint response.
    """
    request = HarnessCaptureRequest(
        task_goal=task_goal,
        reusable_procedure=reusable_procedure,
        summary=summary,
        project=project,
        scope=scope,
        source_agent=source_agent,
        environment=environment,
        trigger_context=trigger_context,
        steps=_items_or_empty(steps),
        commands=_items_or_empty(commands),
        tests=_items_or_empty(tests),
        failures=_items_or_empty(failures),
        fixes=_items_or_empty(fixes),
        artifacts=_items_or_empty(artifacts),
        recall_keywords=_items_or_empty(recall_keywords),
        safety_notes=_items_or_empty(safety_notes),
        metadata={},
    )
    payload = schema_payload(request, exclude_none=True)
    response = await client.post("/memory/contexts/harnesses/check", payload)
    return response


async def alexandria_list_harnesses(
    client: AlexandriaApiClient,
    project: str | None = None,
    scope: ContextScope | None = None,
    source_agent: str | None = None,
    tag: str | None = None,
    limit: int = DEFAULT_HARNESS_LIMIT,
    offset: int = 0,
    include_archived: bool = False,
) -> JSONValue:
    """List saved execution harness contexts.

    Args:
        client: Backend HTTP client.
        project: Optional project filter.
        scope: Optional scope filter.
        source_agent: Optional producing-agent filter.
        tag: Optional tag filter.
        limit: Maximum harnesses to return.
        offset: Pagination offset.
        include_archived: Whether archived harnesses are included.

    Returns:
        Backend harness list response.
    """
    query: JSONObject = {
        "limit": _bounded_harness_limit(limit),
        "offset": max(int(offset), 0),
        "include_archived": str(include_archived).lower(),
    }
    if project is not None:
        query["project"] = project
    if scope is not None:
        query["scope"] = scope.value
    if source_agent is not None:
        query["source_agent"] = source_agent
    if tag is not None:
        query["tag"] = tag
    response = await client.get("/memory/contexts/harnesses", params=query)
    return response


async def alexandria_get_harness(
    client: AlexandriaApiClient,
    context_id: str,
) -> JSONValue:
    """Read one saved execution harness context.

    Args:
        client: Backend HTTP client.
        context_id: Harness context identifier.

    Returns:
        Backend harness response.
    """
    response = await client.get(
        f"/memory/contexts/harnesses/{_path_segment(context_id)}"
    )
    return response


async def alexandria_archive_harness(
    client: AlexandriaApiClient,
    context_id: str,
) -> JSONValue:
    """Archive one saved execution harness context.

    Args:
        client: Backend HTTP client.
        context_id: Harness context identifier.

    Returns:
        Archived harness response.
    """
    response = await client.post(
        f"/memory/contexts/harnesses/{_path_segment(context_id)}/archive", {}
    )
    return response


def _bounded_harness_limit(limit: int) -> int:
    bounded_limit = min(max(int(limit), 1), 50)
    return bounded_limit


def _path_segment(value: str) -> str:
    return quote(value, safe="")


def _items_or_empty(items: list[str] | None) -> list[str]:
    if items is None:
        return []
    return items
