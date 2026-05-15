"""MCP tool gateway backed exclusively by Alexandria-Hermes HTTP APIs."""

from __future__ import annotations

from typing import cast
from urllib.parse import quote

from app.librarian.interface.schemas.librarian.hermes_collaboration_schemas import (
    AskLibrarianRequest,
)
from app.librarian.interface.schemas.librarian.librarian_ops_schemas import (
    CreateCandidateRequest,
)
from app.library.domain.event_enum.item_enums import ItemStatus
from app.library.domain.event_enum.skill_enums import RiskLevel
from app.library.domain.event_enum.usage_enums import SelectionSource
from app.library.interface.schemas.skill.request_schemas import AgentSubmitSkillRequest
from app.library.interface.schemas.usage.usage_schema import UsageRecordRequest
from app.mcp_server.backend_api_client import AlexandriaApiClient
from app.mcp_server.mcp_protocol_enums import McpContextTag
from app.memory.domain.event_enum.context_enums import (
    ContextImportance,
    ContextKind,
    ContextScope,
    ContextSourceType,
    RagStrategy,
)
from app.memory.interface.schemas.context.context_schema import (
    ContextCaptureRequest,
    ContextPrepareCompactRequest,
    ContextSearchRequest,
)
from app.shared.types.extra_types import JSONObject, JSONValue
from app.shared.util.oauth_redaction import without_oauth_sensitive_fields
from pydantic import BaseModel

DEFAULT_CONTEXT_SEARCH_LIMIT = 5
DEFAULT_CONTEXT_SEARCH_STRATEGY = RagStrategy.HYBRID
DEFAULT_CAPTURE_KIND = ContextKind.HANDOFF
DEFAULT_SOURCE_AGENT = "Hermes"
DEFAULT_CAPTURE_SOURCE_TYPE = ContextSourceType.AGENT
DEFAULT_CAPTURE_IMPORTANCE = ContextImportance.MEDIUM
DEFAULT_SKILL_PROVIDER_ID = "hermes-self-acquisition"
DEFAULT_CANDIDATE_AUTHOR = "Hermes"


async def alexandria_search(
    client: AlexandriaApiClient,
    query: str,
    limit: int = DEFAULT_CONTEXT_SEARCH_LIMIT,
    strategy: RagStrategy = DEFAULT_CONTEXT_SEARCH_STRATEGY,
    project: str | None = None,
    kind: ContextKind | None = None,
    include_scopes: list[ContextScope] | None = None,
    workspace_id: str | None = None,
    agent_id: str | None = None,
    user_id: str | None = None,
    session_id: str | None = None,
) -> JSONValue:
    """Search Context Vault and return a Context Pack.

    Args:
        client: Backend HTTP client.
        query: Search query.
        limit: Maximum matches.
        strategy: Retrieval strategy.
        project: Optional project filter.
        kind: Optional context kind filter.

    Returns:
        Backend Context Pack response.
    """
    request = ContextSearchRequest(
        query=query,
        strategy=strategy,
        limit=_bounded_search_limit(limit),
        project=project,
        kind=kind,
        include_scopes=[] if include_scopes is None else include_scopes,
        workspace_id=workspace_id,
        agent_id=agent_id,
        user_id=user_id,
        session_id=session_id,
    )
    payload = _schema_payload(request)
    if payload.get("include_scopes") == []:
        del payload["include_scopes"]
    response = await client.post("/memory/contexts/retrieval/search", payload)
    return response


async def alexandria_recall_context(
    client: AlexandriaApiClient,
    query: str,
    limit: int = DEFAULT_CONTEXT_SEARCH_LIMIT,
    project: str | None = None,
    kind: ContextKind | None = None,
    include_scopes: list[ContextScope] | None = None,
    workspace_id: str | None = None,
    agent_id: str | None = None,
    user_id: str | None = None,
    session_id: str | None = None,
) -> JSONValue:
    """Recall durable context with default hybrid retrieval.

    Args:
        client: Backend HTTP client.
        query: Search query.
        limit: Maximum matches.
        project: Optional project filter.
        kind: Optional context kind filter.

    Returns:
        Backend Context Pack response.
    """
    response = await alexandria_search(
        client,
        query,
        limit,
        DEFAULT_CONTEXT_SEARCH_STRATEGY,
        project,
        kind,
        include_scopes,
        workspace_id,
        agent_id,
        user_id,
        session_id,
    )
    return response


async def alexandria_rag_context(
    client: AlexandriaApiClient,
    query: str,
    strategy: RagStrategy = DEFAULT_CONTEXT_SEARCH_STRATEGY,
    limit: int = DEFAULT_CONTEXT_SEARCH_LIMIT,
    project: str | None = None,
    kind: ContextKind | None = None,
    include_scopes: list[ContextScope] | None = None,
) -> JSONValue:
    """Retrieve a RAG Context Pack with explicit strategy.

    Args:
        client: Backend HTTP client.
        query: Search query.
        strategy: Retrieval strategy.
        limit: Maximum matches.

    Returns:
        Backend Context Pack response.
    """
    response = await alexandria_search(
        client, query, limit, strategy, project, kind, include_scopes
    )
    return response


async def alexandria_capture_context(
    client: AlexandriaApiClient,
    title: str,
    content: str,
    kind: ContextKind = DEFAULT_CAPTURE_KIND,
    summary: str | None = None,
    project: str | None = None,
    scope: ContextScope = ContextScope.PROJECT,
    workspace_id: str | None = None,
    agent_id: str | None = None,
    user_id: str | None = None,
    session_id: str | None = None,
    source_agent: str = DEFAULT_SOURCE_AGENT,
    source_type: ContextSourceType = DEFAULT_CAPTURE_SOURCE_TYPE,
) -> JSONValue:
    """Capture context through the backend Context Vault API.

    Args:
        client: Backend HTTP client.
        title: Context title.
        content: Markdown content.
        kind: Context kind.
        summary: Optional summary.
        project: Optional project scope.
        source_agent: Producing agent name.
        source_type: Source category for agent-authored context.

    Returns:
        Stored context response.
    """
    request = ContextCaptureRequest(
        kind=kind,
        title=title,
        content=content,
        summary=summary,
        project=project,
        scope=scope,
        workspace_id=workspace_id,
        agent_id=agent_id,
        user_id=user_id,
        session_id=session_id,
        visibility=scope,
        source_agent=source_agent,
        source_type=source_type,
        importance=DEFAULT_CAPTURE_IMPORTANCE,
        expires_at=None,
        metadata={},
        tags=[McpContextTag.MCP.value, McpContextTag.CAPTURE.value],
    )
    payload = _schema_payload(request)
    response = await client.post("/memory/contexts/capture", payload)
    return response


async def alexandria_prepare_compact(
    client: AlexandriaApiClient,
    current_goal: str,
    completed: list[str] | None = None,
    in_progress: list[str] | None = None,
    key_decisions: list[str] | None = None,
    next_actions: list[str] | None = None,
    risks: list[str] | None = None,
    project: str | None = None,
    scope: ContextScope = ContextScope.SESSION,
    workspace_id: str | None = None,
    agent_id: str | None = None,
    user_id: str | None = None,
    session_id: str | None = None,
    source_agent: str = DEFAULT_SOURCE_AGENT,
) -> JSONValue:
    """Prepare and save a compact handoff context.

    Args:
        client: Backend HTTP client.
        current_goal: Current work goal.
        completed: Completed bullets.
        in_progress: Active work bullets.
        key_decisions: Decision bullets.
        next_actions: Next action bullets.
        risks: Risk bullets.
        project: Optional project scope.
        source_agent: Producing agent name.

    Returns:
        Stored compact context response.
    """
    request = ContextPrepareCompactRequest(
        project=project,
        source_agent=source_agent,
        current_goal=current_goal,
        completed=_items_or_empty(completed),
        in_progress=_items_or_empty(in_progress),
        key_decisions=_items_or_empty(key_decisions),
        next_actions=_items_or_empty(next_actions),
        risks=_items_or_empty(risks),
        scope=scope,
        workspace_id=workspace_id,
        agent_id=agent_id,
        user_id=user_id,
        session_id=session_id,
        visibility=scope,
    )
    payload = _schema_payload(request)
    response = await client.post("/memory/contexts/prepare-compact", payload)
    return response


async def alexandria_archive_context(
    client: AlexandriaApiClient, context_id: str
) -> JSONValue:
    """Archive a context without exposing hard delete.

    Args:
        client: Backend HTTP client.
        context_id: Context identifier.

    Returns:
        Archived context response.
    """
    response = await client.post(
        f"/memory/contexts/{_path_segment(context_id)}/archive", {}
    )
    return response


async def alexandria_rag_status(client: AlexandriaApiClient) -> JSONValue:
    """Read Context RAG dependency status.

    Args:
        client: Backend HTTP client.

    Returns:
        RAG health response.
    """
    response = await client.get("/memory/contexts/rag/status")
    return response


async def alexandria_get_skill(client: AlexandriaApiClient, item_id: str) -> JSONValue:
    """Read one skill by id.

    Args:
        client: Backend HTTP client.
        item_id: Skill item identifier.

    Returns:
        Skill item response.
    """
    response = await client.get(f"/library/skills/{_path_segment(item_id)}")
    return response


async def alexandria_get_prompt(client: AlexandriaApiClient, item_id: str) -> JSONValue:
    """Read one prompt by id.

    Args:
        client: Backend HTTP client.
        item_id: Prompt item identifier.

    Returns:
        Prompt item response.
    """
    response = await client.get(f"/library/prompts/{_path_segment(item_id)}")
    return response


async def alexandria_request_skill_acquisition(
    client: AlexandriaApiClient,
    prompt: str,
    provider_id: str = DEFAULT_SKILL_PROVIDER_ID,
    category_id: str | None = None,
) -> JSONValue:
    """Request a draft skill candidate from the librarian workflow.

    Args:
        client: Backend HTTP client.
        prompt: Missing-capability description.
        provider_id: Librarian provider identifier or self-acquisition marker.
        category_id: Optional category identifier.

    Returns:
        Draft skill candidate response.
    """
    request = CreateCandidateRequest(
        provider_id=provider_id,
        prompt=prompt,
        category_id=category_id,
    )
    payload = _schema_payload(request)
    response = await client.post("/librarians/create-skill-candidate", payload)
    return response


async def alexandria_submit_skill_candidate(
    client: AlexandriaApiClient,
    title: str,
    purpose: str,
    content: str,
    summary: str | None = None,
    evidence_urls: list[str] | None = None,
    source_summary: str | None = None,
    created_by_name: str = DEFAULT_CANDIDATE_AUTHOR,
) -> JSONValue:
    """Submit a Hermes-authored skill candidate.

    Args:
        client: Backend HTTP client.
        title: Candidate title.
        purpose: Candidate purpose.
        content: Candidate Markdown content.
        summary: Optional summary.
        evidence_urls: Source URLs gathered by Hermes.
        source_summary: Optional source/evidence summary.
        created_by_name: Producing agent name.

    Returns:
        Stored skill response.
    """
    candidate_evidence_urls: list[str] = []
    if evidence_urls is not None:
        candidate_evidence_urls = [url for url in evidence_urls if url.strip()]
    request = AgentSubmitSkillRequest(
        title=title,
        purpose=purpose,
        summary=summary,
        content=content,
        category_id=None,
        tags=[McpContextTag.HERMES.value, McpContextTag.CANDIDATE.value],
        input_schema={},
        output_schema={},
        usage_example=None,
        required_tools=[],
        risk_level=RiskLevel.LOW,
        version="1.0.0",
        created_by_name=created_by_name,
        activate=False,
        status=ItemStatus.DRAFT,
        evidence_urls=candidate_evidence_urls,
        source_summary=source_summary,
    )
    payload = _schema_payload(request)
    response = await client.post("/library/skills/submit-by-agent", payload)
    return response


async def alexandria_record_usage(
    client: AlexandriaApiClient,
    item_id: str,
    item_type: str,
    selection_source: SelectionSource,
    agent_name: str = DEFAULT_SOURCE_AGENT,
    success: bool = True,
    query: str | None = None,
    librarian_provider: str | None = None,
    project: str | None = None,
    task_summary: str | None = None,
    feedback: str | None = None,
) -> JSONValue:
    """Record Hermes usage through the backend usage API.

    Args:
        client: Backend HTTP client.
        item_id: Used library item id.
        item_type: Used item type.
        selection_source: How Hermes selected the item.
        agent_name: Agent recording usage.
        success: Whether the item helped the task.
        query: Optional search or recall query.
        librarian_provider: Optional provider involved in selection.
        project: Optional project scope.
        task_summary: Optional task summary.
        feedback: Optional free-form usefulness note.

    Returns:
        Backend usage record response.
    """
    feedback_payload = _usage_feedback(project, task_summary, feedback)
    request = UsageRecordRequest(
        item_id=item_id,
        item_type=item_type,
        agent_name=agent_name,
        librarian_provider=librarian_provider,
        query=query,
        selection_source=selection_source,
        success=success,
        feedback=feedback_payload,
    )
    payload = _schema_payload(request)
    response = await client.post("/library/usage", payload)
    return response


async def alexandria_ask_librarian(
    client: AlexandriaApiClient,
    prompt: str,
    delegate_to_librarian: bool = False,
    agent_name: str = DEFAULT_SOURCE_AGENT,
    project: str | None = None,
    task_summary: str | None = None,
    provider_id: str | None = None,
    librarian_profile_id: str | None = None,
    librarian_model: str | None = None,
    librarian_role_prompt: str | None = None,
    max_librarian_agents: int | None = None,
    routing_specialties: list[str] | None = None,
) -> JSONValue:
    """Ask for self-acquisition or profile-backed librarian guidance.

    Args:
        client: Backend HTTP client.
        prompt: Missing-capability or research request.
        delegate_to_librarian: Whether Hermes requests librarian guidance.
        agent_name: Requesting agent.
        project: Optional project scope.
        task_summary: Optional task summary.
        provider_id: Optional provider preference.
        librarian_profile_id: Optional agent profile preference.
        librarian_model: Optional request-level model override.
        librarian_role_prompt: Optional request-level role prompt override.
        max_librarian_agents: Optional request-level maximum librarian count.
        routing_specialties: Optional specialty routing hints.

    Returns:
        Backend ask-librarian response.
    """
    request = AskLibrarianRequest(
        prompt=prompt,
        agent_name=agent_name,
        project=project,
        task_summary=task_summary,
        delegate_to_librarian=delegate_to_librarian,
        provider_id=provider_id,
        librarian_profile_id=librarian_profile_id,
        librarian_model=librarian_model,
        librarian_role_prompt=librarian_role_prompt,
        max_librarian_agents=max_librarian_agents,
        routing_specialties=[] if routing_specialties is None else routing_specialties,
    )
    payload = _schema_payload(request)
    response = await client.post("/librarians/ask", payload)
    return response


async def alexandria_librarian_route_preview(
    client: AlexandriaApiClient,
    prompt: str,
    agent_name: str = DEFAULT_SOURCE_AGENT,
    project: str | None = None,
    task_summary: str | None = None,
    provider_id: str | None = None,
    librarian_profile_id: str | None = None,
    librarian_model: str | None = None,
    librarian_role_prompt: str | None = None,
    max_librarian_agents: int | None = None,
    routing_specialties: list[str] | None = None,
) -> JSONValue:
    """Preview librarian routing without delegation.

    Args:
        client: Backend HTTP client.
        prompt: Missing-capability or research request.
        agent_name: Requesting agent.
        project: Optional project scope.
        task_summary: Optional task summary.
        provider_id: Optional provider preference.
        librarian_profile_id: Optional agent profile preference.
        librarian_model: Optional request-level model override.
        librarian_role_prompt: Optional request-level role prompt override.
        max_librarian_agents: Optional request-level maximum librarian count.
        routing_specialties: Optional specialty routing hints.

    Returns:
        Backend route-preview response.
    """
    request = AskLibrarianRequest(
        prompt=prompt,
        agent_name=agent_name,
        project=project,
        task_summary=task_summary,
        delegate_to_librarian=False,
        provider_id=provider_id,
        librarian_profile_id=librarian_profile_id,
        librarian_model=librarian_model,
        librarian_role_prompt=librarian_role_prompt,
        max_librarian_agents=max_librarian_agents,
        routing_specialties=[] if routing_specialties is None else routing_specialties,
    )
    payload = _schema_payload(request)
    response = await client.post("/librarians/route-preview", payload)
    return response


async def alexandria_librarian_job_status(
    client: AlexandriaApiClient,
    job_id: str,
) -> JSONValue:
    """Read status for a guidance-only librarian request.

    Args:
        client: Backend HTTP client.
        job_id: Job id returned by ask-librarian.

    Returns:
        Backend job status response.
    """
    response = await client.get(f"/librarians/jobs/{_path_segment(job_id)}")
    return response


async def alexandria_librarian_oauth_start(
    client: AlexandriaApiClient,
    provider_id: str,
) -> JSONValue:
    """Start OAuth device authorization for a librarian provider.

    Args:
        client: Backend HTTP client.
        provider_id: Librarian provider id.

    Returns:
        Sanitized OAuth start response with codes and credential material removed.
    """
    response = await client.post(
        f"/settings/connections/{_path_segment(provider_id)}/oauth/start", {}
    )
    return without_oauth_sensitive_fields(response)


async def alexandria_librarian_oauth_poll(
    client: AlexandriaApiClient,
    provider_id: str,
) -> JSONValue:
    """Poll OAuth device authorization for a librarian provider.

    Args:
        client: Backend HTTP client.
        provider_id: Librarian provider id.

    Returns:
        Sanitized public OAuth status response.
    """
    response = await client.post(
        f"/settings/connections/{_path_segment(provider_id)}/oauth/poll", {}
    )
    return without_oauth_sensitive_fields(response)


async def alexandria_librarian_oauth_status(
    client: AlexandriaApiClient,
    provider_id: str,
) -> JSONValue:
    """Read public OAuth connection status for a librarian provider.

    Args:
        client: Backend HTTP client.
        provider_id: Librarian provider id.

    Returns:
        Sanitized public OAuth status response.
    """
    response = await client.get(
        f"/settings/connections/{_path_segment(provider_id)}/oauth/status"
    )
    return without_oauth_sensitive_fields(response)


async def alexandria_librarian_oauth_refresh(
    client: AlexandriaApiClient,
    provider_id: str,
) -> JSONValue:
    """Refresh OAuth tokens for a librarian provider when needed.

    Args:
        client: Backend HTTP client.
        provider_id: Librarian provider id.

    Returns:
        Sanitized public OAuth status response.
    """
    response = await client.post(
        f"/settings/connections/{_path_segment(provider_id)}/oauth/refresh", {}
    )
    return without_oauth_sensitive_fields(response)


def _schema_payload(schema: BaseModel) -> JSONObject:
    payload = cast(JSONObject, schema.model_dump(mode="json", exclude_none=True))
    return payload


def _bounded_search_limit(limit: int) -> int:
    bounded_limit = min(max(int(limit), 1), 50)
    return bounded_limit


def _path_segment(value: str) -> str:
    """Return one URL-safe path segment.

    Args:
        value: Untrusted path parameter.

    Returns:
        Percent-encoded path segment safe for backend URL construction.
    """
    return quote(value, safe="")


def _items_or_empty(items: list[str] | None) -> list[str]:
    """Normalize optional bullet lists for compact handoff payloads.

    Args:
        items: Caller-provided list or omitted value.

    Returns:
        Original list or an empty list when omitted.
    """
    if items is None:
        return []
    return items


def _usage_feedback(
    project: str | None,
    task_summary: str | None,
    feedback: str | None,
) -> JSONObject | str | None:
    if project is None and task_summary is None:
        return feedback
    payload: JSONObject = {}
    if project is not None:
        payload["project"] = project
    if task_summary is not None:
        payload["task_summary"] = task_summary
    if feedback is not None:
        payload["comment"] = feedback
    return payload
