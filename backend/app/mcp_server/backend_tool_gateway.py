"""MCP tool gateway backed exclusively by Alexandria-Hermes HTTP APIs."""

from __future__ import annotations

from urllib.parse import quote

from app.librarian.interface.schemas.librarian.hermes_collaboration_schemas import (
    AskLibrarianRequest,
)
from app.librarian.interface.schemas.librarian.librarian_brief_schemas import (
    BudgetPolicySchema,
    LibrarianBriefPreviewRequest,
)
from app.librarian.interface.schemas.librarian.skill_acquisition_schemas import (
    SkillAcquisitionCompletionRequest,
    SkillAcquisitionJobRequest,
)
from app.mcp_server.backend_api_client import AlexandriaApiClient
from app.mcp_server.tools.memory_compact_tools import (
    alexandria_delete_memory_compact as _alexandria_delete_memory_compact,
    alexandria_get_current_memory_compact as _alexandria_get_current_memory_compact,
    alexandria_get_memory_compact as _alexandria_get_memory_compact,
    alexandria_list_memory_compact_artifacts as _alexandria_list_memory_compact_artifacts,
)
from app.memory.domain.event_enum.context_enums import (
    ContextKind,
    ContextScope,
    RagStrategy,
)
from app.memory.interface.schemas.context.context_schema import ContextSearchRequest
from app.shared.serialization.model_codec import schema_payload
from app.shared.types.extra_types import JSONObject, JSONValue
from app.shared.utils.oauth_redaction import without_oauth_sensitive_fields

DEFAULT_CONTEXT_SEARCH_LIMIT = 5
DEFAULT_CONTEXT_SEARCH_STRATEGY = RagStrategy.HYBRID
DEFAULT_SOURCE_AGENT = "Hermes"
DEFAULT_CANDIDATE_AUTHOR = "Hermes"

alexandria_get_current_memory_compact = _alexandria_get_current_memory_compact
alexandria_get_memory_compact = _alexandria_get_memory_compact
alexandria_delete_memory_compact = _alexandria_delete_memory_compact
alexandria_list_memory_compact_artifacts = _alexandria_list_memory_compact_artifacts


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
    payload = schema_payload(request, exclude_none=True)
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


async def alexandria_archive_context(
    client: AlexandriaApiClient, context_id: str
) -> JSONValue:
    """Archive a context without hard deleting it.

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


async def alexandria_delete_context(
    client: AlexandriaApiClient, context_id: str
) -> JSONValue:
    """Hard delete one context.

    Args:
        client: Backend HTTP client.
        context_id: Context identifier.

    Returns:
        Backend delete response, typically None for HTTP 204.
    """
    response = await client.delete(f"/memory/contexts/{_path_segment(context_id)}")
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


async def alexandria_start_skill_acquisition(
    client: AlexandriaApiClient,
    prompt: str,
    agent_name: str = DEFAULT_SOURCE_AGENT,
    project: str | None = None,
    task_summary: str | None = None,
    provider_id: str | None = None,
    librarian_profile_id: str | None = None,
) -> JSONValue:
    """Start a durable async skill-acquisition job.

    Args:
        client: Backend HTTP client.
        prompt: Missing-capability description.
        agent_name: Requesting agent name.
        project: Optional project scope.
        task_summary: Optional current task summary.
        provider_id: Optional preferred librarian provider.
        librarian_profile_id: Optional librarian profile.

    Returns:
        Sanitized durable job response.
    """
    request = SkillAcquisitionJobRequest(
        prompt=prompt,
        agent_name=agent_name,
        project=project,
        task_summary=task_summary,
        provider_id=provider_id,
        librarian_profile_id=librarian_profile_id,
    )
    payload = schema_payload(request, exclude_none=True)
    response = await client.post("/librarians/skill-acquisition-jobs", payload)
    return without_oauth_sensitive_fields(response)


async def alexandria_skill_acquisition_job_status(
    client: AlexandriaApiClient,
    job_id: str,
) -> JSONValue:
    """Poll a durable skill-acquisition job.

    Args:
        client: Backend HTTP client.
        job_id: Skill-acquisition job identifier.

    Returns:
        Sanitized durable job response with result handles when available.
    """
    response = await client.get(
        f"/librarians/skill-acquisition-jobs/{_path_segment(job_id)}"
    )
    return without_oauth_sensitive_fields(response)


async def alexandria_complete_skill_acquisition(
    client: AlexandriaApiClient,
    job_id: str,
    title: str,
    purpose: str,
    content: str,
    summary: str | None = None,
    evidence_urls: list[str] | None = None,
    source_summary: str | None = None,
    next_steps: list[str] | None = None,
    tags: list[str] | None = None,
    required_tools: list[str] | None = None,
    created_by_name: str = DEFAULT_CANDIDATE_AUTHOR,
) -> JSONValue:
    """Complete a durable skill-acquisition job with a structured artifact.

    Args:
        client: Backend HTTP client.
        job_id: Skill-acquisition job identifier.
        title: Candidate title.
        purpose: Candidate purpose.
        content: Candidate Markdown content.
        summary: Optional summary.
        evidence_urls: Source URLs gathered by the agent/librarian.
        source_summary: Optional source/evidence summary.
        next_steps: Optional resume-packet next actions.
        tags: Optional skill tags.
        required_tools: Optional tool dependency names.
        created_by_name: Producing agent/librarian name.

    Returns:
        Completed durable job response with skill/context handles.
    """
    request = SkillAcquisitionCompletionRequest(
        title=title,
        purpose=purpose,
        content=content,
        summary=summary,
        tags=_items_or_empty(tags),
        required_tools=_items_or_empty(required_tools),
        created_by_name=created_by_name,
        evidence_urls=_items_or_empty(evidence_urls),
        source_summary=source_summary,
        next_steps=_items_or_empty(next_steps),
    )
    payload = schema_payload(request, exclude_none=True)
    response = await client.post(
        f"/librarians/skill-acquisition-jobs/{_path_segment(job_id)}/complete",
        payload,
    )
    return response


async def alexandria_librarian_brief_preview(
    client: AlexandriaApiClient,
    prompt: str,
    project: str | None = None,
    max_input_chars: int = 12_000,
    max_source_refs: int = 20,
) -> JSONValue:
    """Compile a budgeted librarian knowledge packet preview.

    Args:
        client: Backend HTTP client.
        prompt: Librarian request text.
        project: Optional project scope.
        max_input_chars: Maximum packet size.
        max_source_refs: Maximum source refs.

    Returns:
        Backend librarian brief preview response.
    """
    request = LibrarianBriefPreviewRequest(
        prompt=prompt,
        project=project,
        budget=BudgetPolicySchema(
            max_input_chars=_bounded_packet_budget(max_input_chars),
            max_source_refs=_bounded_source_ref_limit(max_source_refs),
        ),
    )
    payload = schema_payload(request, exclude_none=True)
    payload.pop("source_refs", None)
    response = await client.post("/librarians/brief-preview", payload)
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
    payload = schema_payload(request, exclude_none=True)
    payload.pop("budget", None)
    payload.pop("source_refs", None)
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
    payload = schema_payload(request, exclude_none=True)
    payload.pop("budget", None)
    payload.pop("source_refs", None)
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


async def alexandria_reindex_vault(client: AlexandriaApiClient) -> JSONValue:
    """Rebuild the Obsidian vault index cache.

    Args:
        client: Backend HTTP client.

    Returns:
        Backend reindex response.
    """
    return await client.post("/obsidian/index/rebuild", {})


async def alexandria_search_vault(
    client: AlexandriaApiClient,
    query: str,
    limit: int = DEFAULT_CONTEXT_SEARCH_LIMIT,
    alexandria_type: str | None = None,
    project: str | None = None,
    tags: list[str] | None = None,
) -> JSONValue:
    """Search Alexandria-managed Obsidian Markdown notes.

    Args:
        client: Backend HTTP client.
        query: Search query.
        limit: Maximum matches.
        alexandria_type: Optional managed note type.
        project: Optional project filter.
        tags: Optional tag filters.

    Returns:
        Backend search response.
    """
    payload: JSONObject = {
        "query": query,
        "limit": _bounded_search_limit(limit),
        "tags": _items_or_empty(tags),
    }
    if alexandria_type is not None:
        payload["alexandria_type"] = alexandria_type
    if project is not None:
        payload["project"] = project
    return await client.post("/obsidian/search", payload)


async def alexandria_read_note(
    client: AlexandriaApiClient,
    note_id: str | None = None,
    path: str | None = None,
) -> JSONValue:
    """Read one Alexandria-managed Obsidian note by id or path.

    Args:
        client: Backend HTTP client.
        note_id: Stable note id.
        path: Vault-relative path.

    Returns:
        Backend note response.
    """
    if path is not None:
        return await client.get("/obsidian/notes/by-path", params={"path": path})
    if note_id is None:
        raise ValueError("note_id or path is required")
    return await client.get(f"/obsidian/notes/{_path_segment(note_id)}")


async def alexandria_save_note(
    client: AlexandriaApiClient,
    title: str,
    body: str,
    alexandria_type: str,
    note_id: str | None = None,
    path: str | None = None,
    project: str | None = None,
    tags: list[str] | None = None,
) -> JSONValue:
    """Save one Alexandria-managed Obsidian Markdown note.

    Args:
        client: Backend HTTP client.
        title: Note title.
        body: Markdown body.
        alexandria_type: Managed note type.
        note_id: Optional stable id.
        path: Optional vault-relative path.
        project: Optional project.
        tags: Optional tags.

    Returns:
        Backend saved note response.
    """
    payload: JSONObject = {
        "title": title,
        "body": body,
        "alexandria_type": alexandria_type,
        "tags": _items_or_empty(tags),
    }
    if note_id is not None:
        payload["id"] = note_id
    if path is not None:
        payload["path"] = path
    if project is not None:
        payload["project"] = project
    return await client.post("/obsidian/notes", payload)


async def alexandria_ask_obsidian_librarian(
    client: AlexandriaApiClient,
    query: str,
    active_note_path: str | None = None,
    selection: str | None = None,
    project: str | None = None,
    save_transcript: bool = False,
    preferred_alexandria_types: list[str] | None = None,
) -> JSONValue:
    """Ask the Obsidian-aware Alexandria librarian.

    Args:
        client: Backend HTTP client.
        query: User question.
        active_note_path: Optional active note path from Obsidian.
        selection: Optional selected Markdown text.
        project: Optional project scope.
        save_transcript: Whether to persist a librarian_chat note.
        preferred_alexandria_types: Optional type filters.

    Returns:
        Backend librarian response.
    """
    payload: JSONObject = {
        "query": query,
        "save_transcript": save_transcript,
        "preferred_alexandria_types": _items_or_empty(preferred_alexandria_types),
    }
    if active_note_path is not None:
        payload["active_note_path"] = active_note_path
    if selection is not None:
        payload["selection"] = selection
    if project is not None:
        payload["project"] = project
    return await client.post("/obsidian/librarian/ask", payload)


def _bounded_packet_budget(limit: int) -> int:
    return min(max(int(limit), 1_000), 120_000)


def _bounded_source_ref_limit(limit: int) -> int:
    return min(max(int(limit), 1), 100)


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
