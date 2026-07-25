"""Register skill acquisition and Hermes librarian MCP tools."""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from app.librarian.domain.event_enum.skill_acquisition_enums import RiskLevel
from app.mcp_server import backend_tool_gateway
from app.mcp_server.backend_api_client import AlexandriaApiClient
from app.shared.types.extra_types import JSONObject, JSONValue


def register_librarian_tools(server: FastMCP, api_client: AlexandriaApiClient) -> None:
    """Register skill acquisition and Hermes librarian MCP tools.

    Args:
        server: FastMCP server receiving tool registrations.
        api_client: Backend HTTP API client used by tool callbacks.
    """

    @server.tool(name="alexandria_search_skills")
    async def _tool_search_skills(
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
        return await backend_tool_gateway.alexandria_search_skills(
            api_client,
            capability=capability,
            task_goal=task_goal,
            project=project,
            environment=environment,
            required_tools=required_tools,
            constraints=constraints,
            risk_tolerance=risk_tolerance,
            success_criteria=success_criteria,
            limit=limit,
        )

    @server.tool(name="alexandria_start_skill_acquisition")
    async def _tool_start_skill_acquisition(
        prompt: str,
        agent_name: str = backend_tool_gateway.DEFAULT_SOURCE_AGENT,
        project: str | None = None,
        task_summary: str | None = None,
        provider_id: str | None = None,
        librarian_profile_id: str | None = None,
        search_snapshot: JSONObject | None = None,
        acquisition_override_reason: str | None = None,
    ) -> JSONValue:
        """Start a durable async skill-acquisition job.

        Args:
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
        return await backend_tool_gateway.alexandria_start_skill_acquisition(
            api_client,
            prompt=prompt,
            agent_name=agent_name,
            project=project,
            task_summary=task_summary,
            provider_id=provider_id,
            librarian_profile_id=librarian_profile_id,
            search_snapshot=search_snapshot,
            acquisition_override_reason=acquisition_override_reason,
        )

    @server.tool(name="alexandria_skill_acquisition_job_status")
    async def _tool_skill_acquisition_job_status(job_id: str) -> JSONValue:
        """Poll a durable skill-acquisition job.

        Args:
            job_id: Skill-acquisition job identifier.

        Returns:
            Sanitized durable job response with result handles when available.
        """
        return await backend_tool_gateway.alexandria_skill_acquisition_job_status(
            api_client, job_id
        )

    @server.tool(name="alexandria_complete_skill_acquisition")
    async def _tool_complete_skill_acquisition(
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
    ) -> JSONValue:
        """Complete a durable skill-acquisition job with a structured artifact.

        Args:
            job_id: Skill-acquisition job identifier.
            title: Candidate title.
            purpose: Candidate purpose.
            content: Candidate Markdown content.
            summary: Optional candidate summary.
            evidence_urls: Source URLs gathered by the agent/librarian.
            source_summary: Optional source/evidence summary.
            next_steps: Optional resume-packet next actions.
            tags: Optional skill tags.
            required_tools: Optional tool dependency names.

        Returns:
            Completed durable job response with skill/context handles.
        """
        return await backend_tool_gateway.alexandria_complete_skill_acquisition(
            api_client,
            job_id=job_id,
            title=title,
            purpose=purpose,
            content=content,
            summary=summary,
            evidence_urls=evidence_urls,
            source_summary=source_summary,
            next_steps=next_steps,
            tags=tags,
            required_tools=required_tools,
        )

    @server.tool(name="alexandria_ask_librarian")
    async def _tool_ask_librarian(
        prompt: str,
        delegate_to_librarian: bool = False,
        agent_name: str = backend_tool_gateway.DEFAULT_SOURCE_AGENT,
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
            prompt: Missing-capability or research request.
            delegate_to_librarian: Whether to request librarian delegation guidance.
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
        return await backend_tool_gateway.alexandria_ask_librarian(
            api_client,
            prompt,
            delegate_to_librarian,
            agent_name,
            project,
            task_summary,
            provider_id,
            librarian_profile_id,
            librarian_model,
            librarian_role_prompt,
            max_librarian_agents,
            routing_specialties,
        )

    @server.tool(name="alexandria_librarian_brief_preview")
    async def _tool_librarian_brief_preview(
        prompt: str,
        project: str | None = None,
        max_input_chars: int = 12_000,
        max_source_refs: int = 20,
    ) -> JSONValue:
        """Compile a budgeted compact/source-ref packet before librarian synthesis.

        Args:
            prompt: Librarian request text.
            project: Optional project scope.
            max_input_chars: Maximum packet size.
            max_source_refs: Maximum lazy-load source refs.

        Returns:
            Backend librarian brief preview response.
        """
        return await backend_tool_gateway.alexandria_librarian_brief_preview(
            api_client, prompt, project, max_input_chars, max_source_refs
        )

    @server.tool(name="alexandria_librarian_route_preview")
    async def _tool_librarian_route_preview(
        prompt: str,
        agent_name: str = backend_tool_gateway.DEFAULT_SOURCE_AGENT,
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
        return await backend_tool_gateway.alexandria_librarian_route_preview(
            api_client,
            prompt,
            agent_name,
            project,
            task_summary,
            provider_id,
            librarian_profile_id,
            librarian_model,
            librarian_role_prompt,
            max_librarian_agents,
            routing_specialties,
        )

    @server.tool(name="alexandria_librarian_job_status")
    async def _tool_librarian_job_status(job_id: str) -> JSONValue:
        """Read status for a guidance-only librarian request.

        Args:
            job_id: Job id returned by ask-librarian.

        Returns:
            Backend job status response.
        """
        return await backend_tool_gateway.alexandria_librarian_job_status(
            api_client, job_id
        )
