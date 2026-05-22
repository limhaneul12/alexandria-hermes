"""Alexandria-Hermes MCP server bootstrap."""

from __future__ import annotations

import argparse
from collections.abc import Sequence

from app.library.domain.event_enum.item_enums import ItemType
from app.library.domain.event_enum.prompt_enums import PromptKind
from app.library.domain.event_enum.search_enums import SearchContentMode
from app.library.domain.event_enum.skill_enums import RiskLevel
from app.library.domain.event_enum.usage_enums import SelectionSource
from app.mcp_server import backend_tool_gateway
from app.mcp_server.backend_api_client import AlexandriaApiClient, AlexandriaApiSettings
from app.mcp_server.mcp_protocol_enums import McpTransport
from app.memory.domain.event_enum.context_enums import (
    ContextKind,
    ContextScope,
    RagStrategy,
)
from app.memory.domain.event_enum.memory_compact_enums import (
    MemoryCompactStatus,
)
from app.shared.types.extra_types import JSONValue
from mcp.server.fastmcp import FastMCP


def create_mcp_server(client: AlexandriaApiClient | None = None) -> FastMCP:
    """Create the Alexandria-Hermes FastMCP server.

    Args:
        client: Optional backend API client for tests.

    Returns:
        Configured FastMCP server.
    """
    if client is None:
        api_client = AlexandriaApiClient(AlexandriaApiSettings.from_env())
    else:
        api_client = client
    server = FastMCP(
        "Alexandria-Hermes Library",
        instructions=(
            "Use these tools to search Alexandria-Hermes skills, prompts, and "
            "Context Vault entries through the backend HTTP API. Do not hard delete."
        ),
        json_response=True,
    )

    @server.tool(name="alexandria_search")
    async def _tool_search(
        query: str,
        limit: int = backend_tool_gateway.DEFAULT_CONTEXT_SEARCH_LIMIT,
        strategy: RagStrategy = backend_tool_gateway.DEFAULT_CONTEXT_SEARCH_STRATEGY,
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
            query: Search query.
            limit: Maximum number of matching contexts.
            strategy: Retrieval strategy.
            project: Optional project filter.
            kind: Optional context kind filter.
            include_scopes: Optional recall scopes.
            workspace_id: Optional workspace filter.
            agent_id: Optional agent filter.
            user_id: Optional user filter.
            session_id: Optional session filter.

        Returns:
            Backend Context Pack response.
        """
        return await backend_tool_gateway.alexandria_search(
            api_client,
            query,
            limit,
            strategy,
            project,
            kind,
            include_scopes,
            workspace_id,
            agent_id,
            user_id,
            session_id,
        )

    @server.tool(name="alexandria_get_skill")
    async def _tool_get_skill(item_id: str) -> JSONValue:
        """Read one Alexandria skill by id.

        Args:
            item_id: Skill item identifier.

        Returns:
            Backend skill response.
        """
        return await backend_tool_gateway.alexandria_get_skill(api_client, item_id)

    @server.tool(name="alexandria_get_prompt")
    async def _tool_get_prompt(item_id: str) -> JSONValue:
        """Read one Alexandria prompt by id.

        Args:
            item_id: Prompt item identifier.

        Returns:
            Backend prompt response.
        """
        return await backend_tool_gateway.alexandria_get_prompt(api_client, item_id)

    @server.tool(name="alexandria_search_library")
    async def _tool_search_library(
        query: str,
        item_types: list[ItemType] | None = None,
        tags: list[str] | None = None,
        limit: int = backend_tool_gateway.DEFAULT_LIBRARY_SEARCH_LIMIT,
        offset: int = 0,
        content_mode: SearchContentMode = SearchContentMode.CANDIDATE,
    ) -> JSONValue:
        """Search library candidates first; get selected items for full content.

        Args:
            query: Search query.
            item_types: Optional item type filters.
            tags: Optional tag filters.
            limit: Maximum candidate count.
            offset: Candidate offset.
            content_mode: Broad search content mode.

        Returns:
            Backend candidate search response without full content.
        """
        return await backend_tool_gateway.alexandria_search_library(
            api_client,
            query,
            item_types,
            tags,
            limit,
            offset,
            content_mode,
        )

    @server.tool(name="alexandria_search_skills")
    async def _tool_search_skills(
        query: str,
        required_tools: list[str] | None = None,
        risk_level: RiskLevel | None = None,
        tags: list[str] | None = None,
        limit: int = backend_tool_gateway.DEFAULT_LIBRARY_SEARCH_LIMIT,
    ) -> JSONValue:
        """Search skill candidates first; call alexandria_get_skill for content.

        Args:
            query: Search query.
            required_tools: Optional required tool filters.
            risk_level: Optional skill risk filter.
            tags: Optional tag filters.
            limit: Maximum candidate count.

        Returns:
            Backend skill candidate response without full content.
        """
        return await backend_tool_gateway.alexandria_search_skills(
            api_client,
            query,
            required_tools,
            risk_level,
            tags,
            limit,
        )

    @server.tool(name="alexandria_search_prompts")
    async def _tool_search_prompts(
        query: str,
        prompt_kind: PromptKind | None = None,
        tags: list[str] | None = None,
        limit: int = backend_tool_gateway.DEFAULT_LIBRARY_SEARCH_LIMIT,
    ) -> JSONValue:
        """Search prompt candidates first; call alexandria_get_prompt for body.

        Args:
            query: Search query.
            prompt_kind: Optional prompt kind filter.
            tags: Optional tag filters.
            limit: Maximum candidate count.

        Returns:
            Backend prompt candidate response without full content.
        """
        return await backend_tool_gateway.alexandria_search_prompts(
            api_client,
            query,
            prompt_kind,
            tags,
            limit,
        )

    @server.tool(name="alexandria_recall_context")
    async def _tool_recall_context(
        query: str,
        limit: int = backend_tool_gateway.DEFAULT_CONTEXT_SEARCH_LIMIT,
        project: str | None = None,
        kind: ContextKind | None = None,
        include_scopes: list[ContextScope] | None = None,
        workspace_id: str | None = None,
        agent_id: str | None = None,
        user_id: str | None = None,
        session_id: str | None = None,
    ) -> JSONValue:
        """Recall durable context by query.

        Args:
            query: Search query.
            limit: Maximum number of matching contexts.
            project: Optional project filter.
            kind: Optional context kind filter.
            include_scopes: Optional recall scopes.
            workspace_id: Optional workspace filter.
            agent_id: Optional agent filter.
            user_id: Optional user filter.
            session_id: Optional session filter.

        Returns:
            Backend Context Pack response.
        """
        return await backend_tool_gateway.alexandria_recall_context(
            api_client,
            query,
            limit,
            project,
            kind,
            include_scopes,
            workspace_id,
            agent_id,
            user_id,
            session_id,
        )

    @server.tool(name="alexandria_rag_context")
    async def _tool_rag_context(
        query: str,
        strategy: RagStrategy = backend_tool_gateway.DEFAULT_CONTEXT_SEARCH_STRATEGY,
        limit: int = backend_tool_gateway.DEFAULT_CONTEXT_SEARCH_LIMIT,
        project: str | None = None,
        kind: ContextKind | None = None,
        include_scopes: list[ContextScope] | None = None,
    ) -> JSONValue:
        """Retrieve a RAG Context Pack by query and strategy.

        Args:
            query: Search query.
            strategy: Retrieval strategy.
            limit: Maximum number of matching contexts.
            project: Optional project filter.
            kind: Optional context kind filter.
            include_scopes: Optional recall scopes.

        Returns:
            Backend Context Pack response.
        """
        return await backend_tool_gateway.alexandria_rag_context(
            api_client, query, strategy, limit, project, kind, include_scopes
        )

    @server.tool(name="alexandria_capture_context")
    async def _tool_capture_context(
        title: str,
        content: str,
        kind: ContextKind = backend_tool_gateway.DEFAULT_CAPTURE_KIND,
        summary: str | None = None,
        project: str | None = None,
        scope: ContextScope = ContextScope.PROJECT,
        workspace_id: str | None = None,
        agent_id: str | None = None,
        user_id: str | None = None,
        session_id: str | None = None,
        source_agent: str = backend_tool_gateway.DEFAULT_SOURCE_AGENT,
    ) -> JSONValue:
        """Capture a Context Vault entry.

        Args:
            title: Context title.
            content: Markdown content to store.
            kind: Context kind.
            summary: Optional context summary.
            project: Optional project scope.
            scope: Recall-routing scope.
            workspace_id: Optional workspace identifier.
            agent_id: Optional agent identifier.
            user_id: Optional user identifier.
            session_id: Optional session identifier.
            source_agent: Producing agent name.

        Returns:
            Stored context response.
        """
        return await backend_tool_gateway.alexandria_capture_context(
            api_client,
            title,
            content,
            kind,
            summary,
            project,
            scope,
            workspace_id,
            agent_id,
            user_id,
            session_id,
            source_agent,
        )

    @server.tool(name="alexandria_capture_harness")
    async def _tool_capture_harness(
        task_goal: str,
        reusable_procedure: str,
        summary: str | None = None,
        project: str | None = None,
        scope: ContextScope = ContextScope.PROJECT,
        workspace_id: str | None = None,
        agent_id: str | None = None,
        user_id: str | None = None,
        session_id: str | None = None,
        source_agent: str = backend_tool_gateway.DEFAULT_SOURCE_AGENT,
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
        """Capture an agent-owned execution harness.

        Args:
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
        return await backend_tool_gateway.alexandria_capture_harness(
            api_client,
            task_goal,
            reusable_procedure,
            summary,
            project,
            scope,
            workspace_id,
            agent_id,
            user_id,
            session_id,
            source_agent,
            environment,
            trigger_context,
            steps,
            commands,
            tests,
            failures,
            fixes,
            artifacts,
            recall_keywords,
            safety_notes,
        )

    @server.tool(name="alexandria_check_harness")
    async def _tool_check_harness(
        task_goal: str,
        reusable_procedure: str,
        summary: str | None = None,
        project: str | None = None,
        scope: ContextScope = ContextScope.PROJECT,
        source_agent: str = backend_tool_gateway.DEFAULT_SOURCE_AGENT,
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
        return await backend_tool_gateway.alexandria_check_harness(
            api_client,
            task_goal,
            reusable_procedure,
            summary,
            project,
            scope,
            source_agent,
            environment,
            trigger_context,
            steps,
            commands,
            tests,
            failures,
            fixes,
            artifacts,
            recall_keywords,
            safety_notes,
        )

    @server.tool(name="alexandria_list_harnesses")
    async def _tool_list_harnesses(
        project: str | None = None,
        scope: ContextScope | None = None,
        source_agent: str | None = None,
        tag: str | None = None,
        limit: int = backend_tool_gateway.DEFAULT_CONTEXT_SEARCH_LIMIT,
        offset: int = 0,
        include_archived: bool = False,
    ) -> JSONValue:
        """List saved execution harnesses.

        Args:
            project: Optional project filter.
            scope: Optional recall scope filter.
            source_agent: Optional producing-agent filter.
            tag: Optional tag filter.
            limit: Maximum harnesses to return.
            offset: Pagination offset.
            include_archived: Whether archived harnesses are included.

        Returns:
            Backend harness list response.
        """
        return await backend_tool_gateway.alexandria_list_harnesses(
            api_client,
            project,
            scope,
            source_agent,
            tag,
            limit,
            offset,
            include_archived,
        )

    @server.tool(name="alexandria_get_harness")
    async def _tool_get_harness(context_id: str) -> JSONValue:
        """Read one saved execution harness.

        Args:
            context_id: Harness context identifier.

        Returns:
            Backend harness response.
        """
        return await backend_tool_gateway.alexandria_get_harness(api_client, context_id)

    @server.tool(name="alexandria_archive_harness")
    async def _tool_archive_harness(context_id: str) -> JSONValue:
        """Archive one saved execution harness.

        Args:
            context_id: Harness context identifier.

        Returns:
            Archived harness response.
        """
        return await backend_tool_gateway.alexandria_archive_harness(
            api_client, context_id
        )

    @server.tool(name="alexandria_list_memory_compact_artifacts")
    async def _tool_list_memory_compact_artifacts(
        project: str | None = None,
        status: MemoryCompactStatus | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> JSONValue:
        """List durable Memory Compact artifacts."""
        return await backend_tool_gateway.alexandria_list_memory_compact_artifacts(
            api_client, project, status, limit, offset
        )

    @server.tool(name="alexandria_get_current_memory_compact")
    async def _tool_get_current_memory_compact(
        project: str | None = None,
    ) -> JSONValue:
        """Read the current Memory Compact for a project."""
        return await backend_tool_gateway.alexandria_get_current_memory_compact(
            api_client, project
        )

    @server.tool(name="alexandria_get_memory_compact")
    async def _tool_get_memory_compact(compact_id: str) -> JSONValue:
        """Read one selected Memory Compact by id."""
        return await backend_tool_gateway.alexandria_get_memory_compact(
            api_client, compact_id
        )

    @server.tool(name="alexandria_delete_memory_compact")
    async def _tool_delete_memory_compact(compact_id: str) -> JSONValue:
        """Hard delete one selected Memory Compact by id."""
        return await backend_tool_gateway.alexandria_delete_memory_compact(
            api_client, compact_id
        )

    @server.tool(name="alexandria_prepare_compact")
    async def _tool_prepare_compact(current_goal: str) -> JSONValue:
        """Prepare and save a compact handoff context.

        Args:
            current_goal: Current work goal to compact.

        Returns:
            Stored compact context response.
        """
        return await backend_tool_gateway.alexandria_prepare_compact(
            api_client, current_goal
        )

    @server.tool(name="alexandria_start_skill_acquisition")
    async def _tool_start_skill_acquisition(
        prompt: str,
        agent_name: str = backend_tool_gateway.DEFAULT_SOURCE_AGENT,
        project: str | None = None,
        task_summary: str | None = None,
        provider_id: str | None = None,
        librarian_profile_id: str | None = None,
    ) -> JSONValue:
        """Start a durable async skill-acquisition job.

        Args:
            prompt: Missing-capability description.
            agent_name: Requesting agent name.
            project: Optional project scope.
            task_summary: Optional current task summary.
            provider_id: Optional preferred librarian provider.
            librarian_profile_id: Optional librarian profile.

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

    @server.tool(name="alexandria_submit_skill_candidate")
    async def _tool_submit_skill_candidate(
        title: str,
        purpose: str,
        content: str,
        summary: str | None = None,
        evidence_urls: list[str] | None = None,
        source_summary: str | None = None,
    ) -> JSONValue:
        """Submit a Hermes-authored skill candidate.

        Args:
            title: Candidate title.
            purpose: Candidate purpose.
            content: Candidate Markdown content.
            summary: Optional candidate summary.
            evidence_urls: Source URLs gathered by Hermes.
            source_summary: Optional source/evidence summary.

        Returns:
            Stored skill response.
        """
        return await backend_tool_gateway.alexandria_submit_skill_candidate(
            api_client,
            title=title,
            purpose=purpose,
            content=content,
            summary=summary,
            evidence_urls=evidence_urls,
            source_summary=source_summary,
        )

    @server.tool(name="alexandria_record_usage")
    async def _tool_record_usage(
        item_id: str,
        item_type: str,
        selection_source: SelectionSource,
        agent_name: str = backend_tool_gateway.DEFAULT_SOURCE_AGENT,
        success: bool = True,
        query: str | None = None,
        librarian_provider: str | None = None,
        project: str | None = None,
        task_summary: str | None = None,
        feedback: str | None = None,
    ) -> JSONValue:
        """Record that Hermes used a skill, prompt, or context.

        Args:
            item_id: Used library item id.
            item_type: Used item type.
            selection_source: How Hermes selected the item.
            agent_name: Agent recording usage.
            success: Whether the item helped the task.
            query: Optional search or recall query.
            librarian_provider: Optional provider involved in selection.
            project: Optional project scope.
            task_summary: Optional task summary.
            feedback: Optional usefulness note.

        Returns:
            Backend usage record response.
        """
        return await backend_tool_gateway.alexandria_record_usage(
            api_client,
            item_id,
            item_type,
            selection_source,
            agent_name,
            success,
            query,
            librarian_provider,
            project,
            task_summary,
            feedback,
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

    @server.tool(name="alexandria_librarian_oauth_start")
    async def _tool_librarian_oauth_start(provider_id: str) -> JSONValue:
        """Start OAuth device authorization for a librarian provider.

        Args:
            provider_id: Librarian provider id.

        Returns:
            Public OAuth start response with secret codes removed.
        """
        return await backend_tool_gateway.alexandria_librarian_oauth_start(
            api_client, provider_id
        )

    @server.tool(name="alexandria_librarian_oauth_poll")
    async def _tool_librarian_oauth_poll(provider_id: str) -> JSONValue:
        """Poll OAuth device authorization for a librarian provider.

        Args:
            provider_id: Librarian provider id.

        Returns:
            Public OAuth status response without token material.
        """
        return await backend_tool_gateway.alexandria_librarian_oauth_poll(
            api_client, provider_id
        )

    @server.tool(name="alexandria_librarian_oauth_status")
    async def _tool_librarian_oauth_status(provider_id: str) -> JSONValue:
        """Read OAuth connection status for a librarian provider.

        Args:
            provider_id: Librarian provider id.

        Returns:
            Public OAuth status response without token material.
        """
        return await backend_tool_gateway.alexandria_librarian_oauth_status(
            api_client, provider_id
        )

    @server.tool(name="alexandria_librarian_oauth_refresh")
    async def _tool_librarian_oauth_refresh(provider_id: str) -> JSONValue:
        """Refresh OAuth tokens for a librarian provider when needed.

        Args:
            provider_id: Librarian provider id.

        Returns:
            Public OAuth status response without token material.
        """
        return await backend_tool_gateway.alexandria_librarian_oauth_refresh(
            api_client, provider_id
        )

    @server.tool(name="alexandria_archive_context")
    async def _tool_archive_context(context_id: str) -> JSONValue:
        """Archive a Context Vault entry without hard delete.

        Args:
            context_id: Context identifier.

        Returns:
            Archived context response.
        """
        return await backend_tool_gateway.alexandria_archive_context(
            api_client, context_id
        )

    @server.tool(name="alexandria_delete_context")
    async def _tool_delete_context(context_id: str) -> JSONValue:
        """Hard delete one Context Vault entry.

        Args:
            context_id: Context identifier.

        Returns:
            Backend delete response, typically null for HTTP 204.
        """
        return await backend_tool_gateway.alexandria_delete_context(
            api_client, context_id
        )

    @server.tool(name="alexandria_rag_status")
    async def _tool_rag_status() -> JSONValue:
        """Read Context RAG health status.

        Returns:
            Backend RAG health response.
        """
        return await backend_tool_gateway.alexandria_rag_status(api_client)

    return server


def build_parser() -> argparse.ArgumentParser:
    """Build the MCP server parser.

    Args:
        None.

    Returns:
        Configured argument parser.
    """
    parser = argparse.ArgumentParser(description="Alexandria-Hermes MCP server")
    parser.add_argument(
        "--transport",
        default=McpTransport.STDIO.value,
        choices=[transport.value for transport in McpTransport],
        help="MCP transport to run.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Run the MCP server.

    Args:
        argv: Optional CLI arguments.

    Returns:
        Process-style exit code.
    """
    parser = build_parser()
    namespace = parser.parse_args(argv)
    server = create_mcp_server()
    server.run(transport=namespace.transport)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
