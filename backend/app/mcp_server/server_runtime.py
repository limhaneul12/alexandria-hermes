"""Alexandria-Hermes MCP server bootstrap."""

from __future__ import annotations

import argparse
from collections.abc import Sequence

from mcp.server.fastmcp import FastMCP

from app.librarian.domain.event_enum.skill_acquisition_enums import RiskLevel
from app.mcp_server import backend_tool_gateway
from app.mcp_server.backend_api_client import AlexandriaApiClient, AlexandriaApiSettings
from app.mcp_server.type_validate.transport_contracts import McpTransport
from app.memory.domain.event_enum.context_enums import (
    ContextKind,
    ContextScope,
    RagStrategy,
)
from app.memory.domain.event_enum.memory_compact_enums import (
    MemoryCompactStatus,
)
from app.shared.types.extra_types import JSONObject, JSONValue

DEFAULT_MCP_TRANSPORT_HOST = "0.0.0.0"


def build_mcp_server(
    client: AlexandriaApiClient | None = None,
    streamable_http_path: str = "/mcp",
    transport_host: str = DEFAULT_MCP_TRANSPORT_HOST,
) -> FastMCP:
    """Build the Alexandria-Hermes FastMCP server.

    Args:
        client: Optional backend API client for tests.
        streamable_http_path: FastMCP Streamable HTTP route path.
        transport_host: Host value used by FastMCP transport security.

    Returns:
        FastMCP server with async tool callbacks registered.
    """
    if client is None:
        api_client = AlexandriaApiClient(AlexandriaApiSettings.from_env())
    else:
        api_client = client
    server = FastMCP(
        "Alexandria-Hermes",
        instructions=(
            "Use these tools for Context Vault, Memory Compact, and librarian "
            "workflows through the backend HTTP API. Do not hard delete unless "
            "a tool name explicitly says delete."
        ),
        json_response=True,
        host=transport_host,
        streamable_http_path=streamable_http_path,
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

    @server.tool(name="alexandria_create_memory_compact")
    async def _tool_create_memory_compact(
        covered_from: str,
        covered_to: str,
        markdown_body: str,
        project: str | None = None,
        status: MemoryCompactStatus = MemoryCompactStatus.DRAFT,
        source_refs: list[dict[str, str]] | None = None,
    ) -> JSONValue:
        """Create a durable Memory Compact artifact."""
        return await backend_tool_gateway.alexandria_create_memory_compact(
            api_client,
            covered_from,
            covered_to,
            markdown_body,
            project,
            status,
            source_refs,
        )

    @server.tool(name="alexandria_mark_memory_compact_current")
    async def _tool_mark_memory_compact_current(compact_id: str) -> JSONValue:
        """Promote one compact to CURRENT."""
        return await backend_tool_gateway.alexandria_mark_memory_compact_current(
            api_client, compact_id
        )

    @server.tool(name="alexandria_archive_memory_compact")
    async def _tool_archive_memory_compact(compact_id: str) -> JSONValue:
        """Archive one compact without deleting it."""
        return await backend_tool_gateway.alexandria_archive_memory_compact(
            api_client, compact_id
        )

    @server.tool(name="alexandria_get_memory_compact")
    async def _tool_get_memory_compact(compact_id: str) -> JSONValue:
        """Read one selected Memory Compact by id."""
        return await backend_tool_gateway.alexandria_get_memory_compact(
            api_client, compact_id
        )

    @server.tool(name="alexandria_review_memory_compact")
    async def _tool_review_memory_compact(
        compact_id: str,
        source_observations: list[dict[str, str]] | None = None,
    ) -> JSONValue:
        """Review one Memory Compact with the librarian quality rubric."""
        return await backend_tool_gateway.alexandria_review_memory_compact(
            api_client, compact_id, source_observations
        )

    @server.tool(name="alexandria_delete_memory_compact")
    async def _tool_delete_memory_compact(compact_id: str) -> JSONValue:
        """Hard delete one selected Memory Compact by id."""
        return await backend_tool_gateway.alexandria_delete_memory_compact(
            api_client, compact_id
        )

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

    @server.tool(name="alexandria_operational_readiness")
    async def _tool_operational_readiness() -> JSONValue:
        """Read operational database, vault, and RAG readiness.

        Returns:
            Backend operational readiness response.
        """
        return await backend_tool_gateway.alexandria_operational_readiness(api_client)

    @server.tool(name="alexandria_recovery_plan")
    async def _tool_recovery_plan(
        trigger: str = "manual",
        actor: str = backend_tool_gateway.DEFAULT_SOURCE_AGENT,
        idempotency_key: str | None = None,
        parent_run_id: str | None = None,
    ) -> JSONValue:
        """Build a read-only operational recovery dry-run plan.

        Args:
            trigger: Recovery plan trigger source.
            actor: Operator or agent requesting the plan.
            idempotency_key: Optional idempotency key.
            parent_run_id: Optional parent recovery run identifier.

        Returns:
            Backend recovery dry-run plan response.
        """
        return await backend_tool_gateway.alexandria_recovery_plan(
            api_client,
            trigger,
            actor,
            idempotency_key,
            parent_run_id,
        )

    @server.tool(name="alexandria_recovery_run")
    async def _tool_recovery_run(
        idempotency_key: str,
        trigger: str = "manual",
        actor: str = backend_tool_gateway.DEFAULT_SOURCE_AGENT,
        parent_run_id: str | None = None,
    ) -> JSONValue:
        """Start or return an idempotent operational recovery run.

        Args:
            idempotency_key: Required idempotency key for the explicit apply.
            trigger: Recovery run trigger source.
            actor: Operator or agent requesting recovery.
            parent_run_id: Optional parent recovery run identifier.

        Returns:
            Backend recovery run response.
        """
        return await backend_tool_gateway.alexandria_recovery_run(
            api_client,
            trigger=trigger,
            actor=actor,
            idempotency_key=idempotency_key,
            parent_run_id=parent_run_id,
        )

    @server.tool(name="alexandria_recovery_run_status")
    async def _tool_recovery_run_status(run_id: str) -> JSONValue:
        """Return a persisted operational recovery run by id.

        Args:
            run_id: Recovery run identifier.

        Returns:
            Backend recovery run response.
        """
        return await backend_tool_gateway.alexandria_recovery_run_status(
            api_client,
            run_id,
        )

    @server.tool(name="alexandria_recovery_retry")
    async def _tool_recovery_retry(
        run_id: str,
        trigger: str = "retry",
        actor: str = backend_tool_gateway.DEFAULT_SOURCE_AGENT,
        idempotency_key: str | None = None,
    ) -> JSONValue:
        """Start or return a parent-linked operational recovery retry.

        Args:
            run_id: Parent recovery run identifier.
            trigger: Recovery retry trigger source.
            actor: Operator or agent requesting retry.
            idempotency_key: Optional retry idempotency key.

        Returns:
            Backend recovery retry response.
        """
        return await backend_tool_gateway.alexandria_recovery_retry(
            api_client,
            run_id,
            trigger,
            actor,
            idempotency_key,
        )

    @server.tool(name="alexandria_recovery_quarantine")
    async def _tool_recovery_quarantine() -> JSONValue:
        """Return stored recovery quarantine artifacts.

        Returns:
            Backend recovery quarantine inventory response.
        """
        return await backend_tool_gateway.alexandria_recovery_quarantine(api_client)

    @server.tool(name="alexandria_reindex_vault")
    async def _tool_reindex_vault() -> JSONValue:
        """Rebuild the Obsidian vault index cache."""
        return await backend_tool_gateway.alexandria_reindex_vault(api_client)

    @server.tool(name="alexandria_search_vault")
    async def _tool_search_vault(
        query: str,
        limit: int = backend_tool_gateway.DEFAULT_CONTEXT_SEARCH_LIMIT,
        alexandria_type: str | None = None,
        project: str | None = None,
        tags: list[str] | None = None,
    ) -> JSONValue:
        """Search Alexandria-managed Obsidian Markdown notes."""
        return await backend_tool_gateway.alexandria_search_vault(
            api_client, query, limit, alexandria_type, project, tags
        )

    @server.tool(name="alexandria_librarian_review_queue")
    async def _tool_librarian_review_queue(
        project: str | None = None,
        scope_path: str | None = None,
        limit: int = 20,
    ) -> JSONValue:
        """List Obsidian notes that need librarian curation."""
        return await backend_tool_gateway.alexandria_librarian_review_queue(
            api_client, project, scope_path, limit
        )

    @server.tool(name="alexandria_librarian_review_move_plan")
    async def _tool_librarian_review_move_plan(
        project: str | None = None,
        scope_path: str | None = None,
        limit: int = 20,
    ) -> JSONValue:
        """Build a dry-run safe move plan from librarian review candidates."""
        return await backend_tool_gateway.alexandria_librarian_review_move_plan(
            api_client, project, scope_path, limit
        )

    @server.tool(name="alexandria_librarian_review_apply_moves")
    async def _tool_librarian_review_apply_moves(
        project: str | None = None,
        scope_path: str | None = None,
        limit: int = 20,
        report_path: str | None = None,
        reindex: bool = True,
        verification_query: str | None = None,
        confirm_apply: bool = False,
    ) -> JSONValue:
        """Apply safe moves generated from librarian review candidates."""
        return await backend_tool_gateway.alexandria_librarian_review_apply_moves(
            api_client,
            project,
            scope_path,
            limit,
            report_path,
            reindex,
            verification_query,
            confirm_apply,
        )

    @server.tool(name="alexandria_librarian_vault_inventory")
    async def _tool_librarian_vault_inventory(
        scope_path: str | None = None,
    ) -> JSONValue:
        """Inventory managed Obsidian notes for librarian operations."""
        return await backend_tool_gateway.alexandria_librarian_vault_inventory(
            api_client, scope_path
        )

    @server.tool(name="alexandria_librarian_vault_path_search")
    async def _tool_librarian_vault_path_search(
        query: str,
        scope_path: str | None = None,
    ) -> JSONValue:
        """Search managed Obsidian note paths and metadata."""
        return await backend_tool_gateway.alexandria_librarian_vault_path_search(
            api_client, query, scope_path
        )

    @server.tool(name="alexandria_librarian_vault_move_plan")
    async def _tool_librarian_vault_move_plan(
        moves: list[dict[str, str]],
    ) -> JSONValue:
        """Build a dry-run safe move plan for explicit vault moves."""
        return await backend_tool_gateway.alexandria_librarian_vault_move_plan(
            api_client, moves
        )

    @server.tool(name="alexandria_librarian_vault_apply_moves")
    async def _tool_librarian_vault_apply_moves(
        moves: list[dict[str, str]],
        report_path: str | None = None,
        reindex: bool = True,
        verification_query: str | None = None,
    ) -> JSONValue:
        """Apply explicit safe vault moves through the librarian workflow."""
        return await backend_tool_gateway.alexandria_librarian_vault_apply_moves(
            api_client,
            moves,
            report_path,
            reindex,
            verification_query,
        )

    @server.tool(name="alexandria_librarian_readiness")
    async def _tool_librarian_readiness(
        project: str | None = None,
        max_compact_age_days: int = 30,
    ) -> JSONValue:
        """Return librarian/second-brain readiness in one call."""
        return await backend_tool_gateway.alexandria_librarian_readiness(
            api_client, project, max_compact_age_days
        )

    @server.tool(name="alexandria_librarian_refresh_current_compact")
    async def _tool_librarian_refresh_current_compact(
        project: str | None = None,
        max_compact_age_days: int = 30,
        apply: bool = False,
        force: bool = False,
        covered_to: str | None = None,
    ) -> JSONValue:
        """Plan or apply a CURRENT compact refresh from readiness evidence."""
        return await backend_tool_gateway.alexandria_librarian_refresh_current_compact(
            api_client,
            project,
            max_compact_age_days,
            apply,
            force,
            covered_to,
        )

    @server.tool(name="alexandria_read_note")
    async def _tool_read_note(
        note_id: str | None = None,
        path: str | None = None,
    ) -> JSONValue:
        """Read one Alexandria-managed Obsidian note by id or path."""
        return await backend_tool_gateway.alexandria_read_note(
            api_client, note_id, path
        )

    @server.tool(name="alexandria_get_related_notes")
    async def _tool_get_related_notes(
        note_id: str | None = None,
        path: str | None = None,
        limit: int = backend_tool_gateway.DEFAULT_CONTEXT_SEARCH_LIMIT,
    ) -> JSONValue:
        """Read graph-related Obsidian notes by id or path."""
        return await backend_tool_gateway.alexandria_get_related_notes(
            api_client, note_id, path, limit
        )

    @server.tool(name="alexandria_save_note")
    async def _tool_save_note(
        title: str,
        body: str,
        alexandria_type: str,
        note_id: str | None = None,
        path: str | None = None,
        project: str | None = None,
        tags: list[str] | None = None,
        status: str = "active",
        source: str = "mcp",
        frontmatter: dict[str, JSONValue] | None = None,
    ) -> JSONValue:
        """Save one Alexandria-managed Obsidian Markdown note."""
        return await backend_tool_gateway.alexandria_save_note(
            api_client,
            title,
            body,
            alexandria_type,
            note_id,
            path,
            project,
            tags,
            status,
            source,
            frontmatter,
        )

    @server.tool(name="alexandria_ask_obsidian_librarian")
    async def _tool_ask_obsidian_librarian(
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
        """Ask the Obsidian-aware Alexandria librarian."""
        return await backend_tool_gateway.alexandria_ask_obsidian_librarian(
            api_client,
            query,
            active_note_path,
            selection,
            project,
            save_transcript,
            preferred_alexandria_types,
            delegate_to_librarian,
            provider_id,
            profile_id,
        )

    return server


def main(argv: Sequence[str] | None = None) -> int:
    """Run the Alexandria-Hermes FastMCP server.

    Args:
        argv: Optional process arguments without the executable name.

    Returns:
        Process-style exit code after the MCP server exits normally.
    """
    parser = argparse.ArgumentParser(prog="alexandria-hermes mcp serve")
    parser.add_argument(
        "--transport",
        choices=[transport.value for transport in McpTransport],
        default=McpTransport.STDIO.value,
        help="MCP transport protocol.",
    )
    args = parser.parse_args(argv)
    server = build_mcp_server(transport_host=DEFAULT_MCP_TRANSPORT_HOST)
    server.run(transport=args.transport)
    return 0
