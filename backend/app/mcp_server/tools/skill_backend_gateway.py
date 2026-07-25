"""Skill acquisition and Hermes librarian MCP HTTP gateway functions."""

from __future__ import annotations

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
    SkillAcquisitionJobRequest,
    SkillCapabilitySearchRequest,
)
from app.mcp_server.backend_api_client import AlexandriaApiClient
from app.mcp_server.tools.backend_gateway_policy import (
    DEFAULT_CANDIDATE_AUTHOR,
    DEFAULT_SOURCE_AGENT,
    _bounded_packet_budget,
    _bounded_source_ref_limit,
    _evidence_items_or_empty,
    _items_or_empty,
    _path_segment,
)
from app.shared.serialization.model_codec import schema_payload
from app.shared.types.extra_types import JSONObject, JSONValue
from app.shared.utils.oauth_redaction import without_oauth_sensitive_fields


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
