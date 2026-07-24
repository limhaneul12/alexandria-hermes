"""MCP tool gateway backed exclusively by Alexandria-Hermes HTTP APIs."""

from __future__ import annotations

from urllib.parse import quote

from app.librarian.domain.event_enum.skill_acquisition_enums import RiskLevel
from app.librarian.interface.schemas.librarian.hermes_collaboration_schemas import (
    AskLibrarianRequest,
)
from app.librarian.interface.schemas.librarian.librarian_brief_schemas import (
    BudgetPolicySchema,
    LibrarianBriefPreviewRequest,
)
from app.librarian.interface.schemas.librarian.skill_acquisition_schemas import (
    SkillAcquisitionCompletionRequest,
    SkillAcquisitionEvidenceItemRequest,
    SkillAcquisitionJobRequest,
    SkillCapabilitySearchRequest,
)
from app.mcp_server.backend_api_client import AlexandriaApiClient
from app.mcp_server.tools.librarian_readiness_tools import (
    alexandria_librarian_readiness as _alexandria_librarian_readiness,
    alexandria_librarian_refresh_current_compact as _alexandria_librarian_refresh_current_compact,
)
from app.mcp_server.tools.memory_compact_tools import (
    alexandria_archive_memory_compact as _alexandria_archive_memory_compact,
    alexandria_create_memory_compact as _alexandria_create_memory_compact,
    alexandria_delete_memory_compact as _alexandria_delete_memory_compact,
    alexandria_get_current_memory_compact as _alexandria_get_current_memory_compact,
    alexandria_get_memory_compact as _alexandria_get_memory_compact,
    alexandria_list_memory_compact_artifacts as _alexandria_list_memory_compact_artifacts,
    alexandria_mark_memory_compact_current as _alexandria_mark_memory_compact_current,
    alexandria_review_memory_compact as _alexandria_review_memory_compact,
)
from app.mcp_server.type_validate.librarian_review_gateway_contracts import (
    empty_review_apply_payload,
    review_apply_confirmation_required_payload,
    review_move_plan_has_moves,
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
alexandria_create_memory_compact = _alexandria_create_memory_compact
alexandria_mark_memory_compact_current = _alexandria_mark_memory_compact_current
alexandria_archive_memory_compact = _alexandria_archive_memory_compact
alexandria_review_memory_compact = _alexandria_review_memory_compact
alexandria_librarian_readiness = _alexandria_librarian_readiness
alexandria_librarian_refresh_current_compact = (
    _alexandria_librarian_refresh_current_compact
)
alexandria_delete_memory_compact = _alexandria_delete_memory_compact
alexandria_list_memory_compact_artifacts = _alexandria_list_memory_compact_artifacts


async def alexandria_search(
    client: AlexandriaApiClient,
    request: ContextSearchRequest,
) -> JSONValue:
    """Search Context Vault and return a Context Pack.

    Args:
        client: Backend HTTP client.
        request: Validated Context search boundary contract.

    Returns:
        Backend Context Pack response.
    """
    payload = schema_payload(request, exclude_none=True)
    if payload.get("include_scopes") == []:
        del payload["include_scopes"]
    if payload.get("include_lifecycle_statuses") == []:
        del payload["include_lifecycle_statuses"]
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
        ContextSearchRequest(
            query=query,
            limit=_bounded_search_limit(limit),
            strategy=DEFAULT_CONTEXT_SEARCH_STRATEGY,
            project=project,
            kind=kind,
            include_scopes=[] if include_scopes is None else include_scopes,
            workspace_id=workspace_id,
            agent_id=agent_id,
            user_id=user_id,
            session_id=session_id,
        ),
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
        client,
        ContextSearchRequest(
            query=query,
            strategy=strategy,
            limit=_bounded_search_limit(limit),
            project=project,
            kind=kind,
            include_scopes=[] if include_scopes is None else include_scopes,
        ),
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


async def alexandria_operational_readiness(
    client: AlexandriaApiClient,
) -> JSONValue:
    """Read operational database, vault, and RAG readiness.

    Args:
        client: Backend HTTP client.

    Returns:
        Operational readiness response.
    """
    response = await client.get("/operations/readiness")
    return response


async def alexandria_recovery_plan(
    client: AlexandriaApiClient,
    trigger: str = "manual",
    actor: str = DEFAULT_SOURCE_AGENT,
    idempotency_key: str | None = None,
    parent_run_id: str | None = None,
) -> JSONValue:
    """Build a read-only operational recovery dry-run plan.

    Args:
        client: Backend HTTP client.
        trigger: Recovery plan trigger source.
        actor: Operator or agent requesting the plan.
        idempotency_key: Optional idempotency key.
        parent_run_id: Optional parent recovery run identifier.

    Returns:
        Recovery dry-run plan response.
    """
    payload: JSONObject = {
        "trigger": trigger,
        "actor": actor,
    }
    if idempotency_key is not None:
        payload["idempotency_key"] = idempotency_key
    if parent_run_id is not None:
        payload["parent_run_id"] = parent_run_id
    response = await client.post("/operations/recovery/plan", payload)
    return response


async def alexandria_recovery_run(
    client: AlexandriaApiClient,
    trigger: str = "manual",
    actor: str = DEFAULT_SOURCE_AGENT,
    idempotency_key: str | None = None,
    parent_run_id: str | None = None,
) -> JSONValue:
    """Start or return an idempotent operational recovery run.

    Args:
        client: Backend HTTP client.
        trigger: Recovery run trigger source.
        actor: Operator or agent requesting recovery.
        idempotency_key: Required idempotency key for the explicit apply.
        parent_run_id: Optional parent recovery run identifier.

    Returns:
        Recovery run response.
    """
    required_idempotency_key = _required_recovery_run_idempotency_key(idempotency_key)
    payload: JSONObject = {
        "trigger": trigger,
        "actor": actor,
        "idempotency_key": required_idempotency_key,
    }
    if parent_run_id is not None:
        payload["parent_run_id"] = parent_run_id
    response = await client.post("/operations/recovery/runs", payload)
    return response


async def alexandria_recovery_run_status(
    client: AlexandriaApiClient,
    run_id: str,
) -> JSONValue:
    """Return a persisted operational recovery run by id.

    Args:
        client: Backend HTTP client.
        run_id: Recovery run identifier.

    Returns:
        Recovery run response.
    """
    response = await client.get(f"/operations/recovery/runs/{_path_segment(run_id)}")
    return response


async def alexandria_recovery_retry(
    client: AlexandriaApiClient,
    run_id: str,
    trigger: str = "retry",
    actor: str = DEFAULT_SOURCE_AGENT,
    idempotency_key: str | None = None,
) -> JSONValue:
    """Start or return a parent-linked operational recovery retry.

    Args:
        client: Backend HTTP client.
        run_id: Parent recovery run identifier.
        trigger: Recovery retry trigger source.
        actor: Operator or agent requesting retry.
        idempotency_key: Optional retry idempotency key.

    Returns:
        Recovery retry run response.
    """
    payload: JSONObject = {
        "trigger": trigger,
        "actor": actor,
    }
    if idempotency_key is not None:
        payload["idempotency_key"] = idempotency_key
    response = await client.post(
        f"/operations/recovery/runs/{_path_segment(run_id)}/retry",
        payload,
    )
    return response


async def alexandria_recovery_quarantine(
    client: AlexandriaApiClient,
) -> JSONValue:
    """Return stored recovery quarantine artifacts.

    Args:
        client: Backend HTTP client.

    Returns:
        Recovery quarantine inventory response.
    """
    response = await client.get("/operations/recovery/quarantine")
    return response


async def alexandria_search_skills(
    client: AlexandriaApiClient,
    capability: str,
    task_goal: str | None = None,
    project: str | None = None,
    environment: str | None = None,
    required_tools: list[str] | None = None,
    constraints: list[str] | None = None,
    risk_tolerance: RiskLevel = RiskLevel.MEDIUM,
    success_criteria: list[str] | None = None,
    limit: int = 5,
) -> JSONValue:
    """Search reusable skill notes before starting acquisition.

    Args:
        client: Backend HTTP client.
        capability: Needed capability.
        task_goal: Current task goal.
        project: Optional project scope.
        environment: Runtime/framework context.
        required_tools: Tool names the skill must support.
        constraints: Operational or safety constraints.
        risk_tolerance: Maximum acceptable risk level.
        success_criteria: Criteria for sufficient reuse.
        limit: Maximum candidates.

    Returns:
        Search-first sufficiency decision.
    """
    request = SkillCapabilitySearchRequest(
        capability=capability,
        task_goal=task_goal,
        project=project,
        environment=environment,
        required_tools=_items_or_empty(required_tools),
        constraints=_items_or_empty(constraints),
        risk_tolerance=risk_tolerance,
        success_criteria=_items_or_empty(success_criteria),
        limit=max(1, min(limit, 10)),
    )
    payload = schema_payload(request, exclude_none=True)
    response = await client.post("/librarians/skill-library/search", payload)
    return without_oauth_sensitive_fields(response)


async def alexandria_start_skill_acquisition(
    client: AlexandriaApiClient,
    prompt: str,
    agent_name: str = DEFAULT_SOURCE_AGENT,
    project: str | None = None,
    task_summary: str | None = None,
    provider_id: str | None = None,
    librarian_profile_id: str | None = None,
    search_snapshot: JSONObject | None = None,
    acquisition_override_reason: str | None = None,
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
        search_snapshot: Optional search-first decision snapshot.
        acquisition_override_reason: Explicit reason for starting without search.

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
        search_snapshot=search_snapshot,
        acquisition_override_reason=acquisition_override_reason,
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
    evidence_items: list[JSONObject] | None = None,
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
        evidence_items: Claim-linked structured evidence gathered by the
            agent/librarian.
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
        evidence_items=_evidence_items_or_empty(evidence_items),
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


async def alexandria_librarian_review_queue(
    client: AlexandriaApiClient,
    project: str | None = None,
    scope_path: str | None = None,
    limit: int = 20,
) -> JSONValue:
    """List notes that need librarian curation.

    Args:
        client: Backend HTTP client.
        project: Optional project filter.
        scope_path: Optional vault-relative scope.
        limit: Maximum candidates to return.

    Returns:
        Backend review queue response.
    """
    payload: JSONObject = {"limit": min(max(int(limit), 1), 200)}
    if project is not None:
        payload["project"] = project
    if scope_path is not None:
        payload["scope_path"] = scope_path
    return await client.post("/obsidian/librarian/review-queue", payload)


async def alexandria_librarian_review_move_plan(
    client: AlexandriaApiClient,
    project: str | None = None,
    scope_path: str | None = None,
    limit: int = 20,
) -> JSONValue:
    """Build a dry-run move plan from librarian review candidates.

    Args:
        client: Backend HTTP client.
        project: Optional project filter.
        scope_path: Optional vault-relative scope.
        limit: Maximum candidates to plan from.

    Returns:
        Backend safe move-plan response.
    """
    payload: JSONObject = {"limit": min(max(int(limit), 1), 200)}
    if project is not None:
        payload["project"] = project
    if scope_path is not None:
        payload["scope_path"] = scope_path
    return await client.post("/obsidian/librarian/review-queue/move-plan", payload)


async def alexandria_librarian_review_apply_moves(
    client: AlexandriaApiClient,
    project: str | None = None,
    scope_path: str | None = None,
    limit: int = 20,
    report_path: str | None = None,
    reindex: bool = True,
    verification_query: str | None = None,
    confirm_apply: bool = False,
) -> JSONValue:
    """Apply safe moves generated from librarian review candidates.

    Args:
        client: Backend HTTP client.
        project: Optional project filter.
        scope_path: Optional vault-relative scope.
        limit: Maximum candidates to apply.
        report_path: Optional report path stem.
        reindex: Whether to reindex after moving.
        verification_query: Optional verification search query.
        confirm_apply: Required confirmation when the move plan has moves.

    Returns:
        Backend safe move application report.
    """
    move_plan = await alexandria_librarian_review_move_plan(
        client,
        project=project,
        scope_path=scope_path,
        limit=limit,
    )
    if not review_move_plan_has_moves(move_plan):
        return empty_review_apply_payload(move_plan)
    if not confirm_apply:
        return review_apply_confirmation_required_payload(move_plan)

    payload: JSONObject = {
        "limit": min(max(int(limit), 1), 200),
        "reindex": reindex,
    }
    if project is not None:
        payload["project"] = project
    if scope_path is not None:
        payload["scope_path"] = scope_path
    if report_path is not None:
        payload["report_path"] = report_path
    if verification_query is not None:
        payload["verification_query"] = verification_query
    return await client.post("/obsidian/librarian/review-queue/apply-moves", payload)


async def alexandria_librarian_vault_inventory(
    client: AlexandriaApiClient,
    scope_path: str | None = None,
) -> JSONValue:
    """Inventory managed Obsidian notes for librarian operations.

    Args:
        client: Backend HTTP client.
        scope_path: Optional vault-relative scope.

    Returns:
        Backend inventory response.
    """
    payload: JSONObject = {}
    if scope_path is not None:
        payload["scope_path"] = scope_path
    return await client.post("/obsidian/librarian/vault/inventory", payload)


async def alexandria_librarian_vault_path_search(
    client: AlexandriaApiClient,
    query: str,
    scope_path: str | None = None,
) -> JSONValue:
    """Search managed Obsidian note paths and metadata.

    Args:
        client: Backend HTTP client.
        query: Keyword/path fragment.
        scope_path: Optional vault-relative scope.

    Returns:
        Backend inventory response containing matching notes.
    """
    payload: JSONObject = {"query": query}
    if scope_path is not None:
        payload["scope_path"] = scope_path
    return await client.post("/obsidian/librarian/vault/path-search", payload)


async def alexandria_librarian_vault_move_plan(
    client: AlexandriaApiClient,
    moves: list[dict[str, str]],
) -> JSONValue:
    """Build a dry-run safe move plan for explicit vault moves.

    Args:
        client: Backend HTTP client.
        moves: Explicit source/destination/reason move payloads.

    Returns:
        Backend safe move-plan response.
    """
    return await client.post(
        "/obsidian/librarian/vault/move-plan",
        {"moves": _move_payloads(moves)},
    )


async def alexandria_librarian_vault_apply_moves(
    client: AlexandriaApiClient,
    moves: list[dict[str, str]],
    report_path: str | None = None,
    reindex: bool = True,
    verification_query: str | None = None,
) -> JSONValue:
    """Apply explicit safe vault moves through the librarian workflow.

    Args:
        client: Backend HTTP client.
        moves: Explicit source/destination/reason move payloads.
        report_path: Optional report path stem.
        reindex: Whether to reindex after moving.
        verification_query: Optional verification query.

    Returns:
        Backend safe move application report.
    """
    payload: JSONObject = {
        "moves": _move_payloads(moves),
        "reindex": reindex,
    }
    if report_path is not None:
        payload["report_path"] = report_path
    if verification_query is not None:
        payload["verification_query"] = verification_query
    return await client.post("/obsidian/librarian/vault/apply-moves", payload)


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


async def alexandria_get_related_notes(
    client: AlexandriaApiClient,
    note_id: str | None = None,
    path: str | None = None,
    limit: int = DEFAULT_CONTEXT_SEARCH_LIMIT,
) -> JSONValue:
    """Read graph-related Obsidian notes by id or path.

    Args:
        client: Backend HTTP client.
        note_id: Stable note id.
        path: Vault-relative note path.
        limit: Maximum related notes.

    Returns:
        Backend related notes response.
    """
    bounded_limit = _bounded_search_limit(limit)
    if path is not None:
        return await client.get(
            "/obsidian/notes/by-path/related",
            params={"path": path, "limit": bounded_limit},
        )
    if note_id is None:
        raise ValueError("note_id or path is required")
    return await client.get(
        f"/obsidian/notes/{_path_segment(note_id)}/related",
        params={"limit": bounded_limit},
    )


async def alexandria_save_note(
    client: AlexandriaApiClient,
    title: str,
    body: str,
    alexandria_type: str,
    note_id: str | None = None,
    path: str | None = None,
    project: str | None = None,
    tags: list[str] | None = None,
    status: str = "active",
    source: str = "mcp",
    frontmatter: JSONObject | None = None,
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
        status: Frontmatter lifecycle status.
        source: Frontmatter source marker.
        frontmatter: Optional extra frontmatter object.

    Returns:
        Backend saved note response.
    """
    payload: JSONObject = {
        "title": title,
        "body": body,
        "alexandria_type": alexandria_type,
        "tags": _items_or_empty(tags),
        "status": status,
        "source": source,
        "frontmatter": {} if frontmatter is None else dict(frontmatter),
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
    delegate_to_librarian: bool = False,
    provider_id: str | None = None,
    profile_id: str | None = None,
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
        delegate_to_librarian: Whether to request provider delegation hooks.
        provider_id: Optional preferred provider id.
        profile_id: Optional preferred profile id.

    Returns:
        Backend librarian response.
    """
    payload: JSONObject = {
        "query": query,
        "save_transcript": save_transcript,
        "preferred_alexandria_types": _items_or_empty(preferred_alexandria_types),
        "delegate_to_librarian": delegate_to_librarian,
    }
    if active_note_path is not None:
        payload["active_note_path"] = active_note_path
    if selection is not None:
        payload["selection"] = selection
    if project is not None:
        payload["project"] = project
    if provider_id is not None:
        payload["provider_id"] = provider_id
    if profile_id is not None:
        payload["profile_id"] = profile_id
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


def _required_recovery_run_idempotency_key(value: str | None) -> str:
    if value is None or not value.strip():
        raise ValueError("idempotency_key is required for alexandria_recovery_run")
    return value.strip()


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


def _evidence_items_or_empty(
    items: list[JSONObject] | None,
) -> list[SkillAcquisitionEvidenceItemRequest]:
    """Normalize optional structured evidence payloads for job completion.

    Args:
        items: Caller-provided evidence item dictionaries or omitted value.

    Returns:
        Validated evidence item schemas, or an empty list when omitted.
    """
    if items is None:
        return []
    return [SkillAcquisitionEvidenceItemRequest.model_validate(item) for item in items]


def _move_payloads(moves: list[dict[str, str]]) -> list[JSONObject]:
    return [
        {
            "source_path": move["source_path"],
            "destination_path": move["destination_path"],
            "reason": move["reason"],
        }
        for move in moves
    ]
