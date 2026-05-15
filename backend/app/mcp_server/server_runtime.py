"""Alexandria-Hermes MCP server bootstrap."""

from __future__ import annotations

import argparse
from collections.abc import Sequence

from app.library.domain.event_enum.context_enums import ContextKind, RagStrategy
from app.mcp_server import backend_tool_gateway
from app.mcp_server.backend_api_client import AlexandriaApiClient, AlexandriaApiSettings
from app.mcp_server.mcp_protocol_enums import McpTransport
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
    ) -> JSONValue:
        """Search Context Vault and return a Context Pack.

        Args:
            query: Search query.
            limit: Maximum number of matching contexts.
            strategy: Retrieval strategy.
            project: Optional project filter.
            kind: Optional context kind filter.

        Returns:
            Backend Context Pack response.
        """
        return await backend_tool_gateway.alexandria_search(
            api_client, query, limit, strategy, project, kind
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

    @server.tool(name="alexandria_recall_context")
    async def _tool_recall_context(
        query: str,
        limit: int = backend_tool_gateway.DEFAULT_CONTEXT_SEARCH_LIMIT,
        project: str | None = None,
        kind: ContextKind | None = None,
    ) -> JSONValue:
        """Recall durable context by query.

        Args:
            query: Search query.
            limit: Maximum number of matching contexts.
            project: Optional project filter.
            kind: Optional context kind filter.

        Returns:
            Backend Context Pack response.
        """
        return await backend_tool_gateway.alexandria_recall_context(
            api_client, query, limit, project, kind
        )

    @server.tool(name="alexandria_rag_context")
    async def _tool_rag_context(
        query: str,
        strategy: RagStrategy = backend_tool_gateway.DEFAULT_CONTEXT_SEARCH_STRATEGY,
        limit: int = backend_tool_gateway.DEFAULT_CONTEXT_SEARCH_LIMIT,
    ) -> JSONValue:
        """Retrieve a RAG Context Pack by query and strategy.

        Args:
            query: Search query.
            strategy: Retrieval strategy.
            limit: Maximum number of matching contexts.

        Returns:
            Backend Context Pack response.
        """
        return await backend_tool_gateway.alexandria_rag_context(
            api_client, query, strategy, limit
        )

    @server.tool(name="alexandria_capture_context")
    async def _tool_capture_context(
        title: str,
        content: str,
        kind: ContextKind = backend_tool_gateway.DEFAULT_CAPTURE_KIND,
        summary: str | None = None,
        project: str | None = None,
        source_agent: str = backend_tool_gateway.DEFAULT_SOURCE_AGENT,
    ) -> JSONValue:
        """Capture a Context Vault entry.

        Args:
            title: Context title.
            content: Markdown content to store.
            kind: Context kind.
            summary: Optional context summary.
            project: Optional project scope.
            source_agent: Producing agent name.

        Returns:
            Stored context response.
        """
        return await backend_tool_gateway.alexandria_capture_context(
            api_client, title, content, kind, summary, project, source_agent
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

    @server.tool(name="alexandria_request_skill_acquisition")
    async def _tool_request_skill_acquisition(prompt: str) -> JSONValue:
        """Request a draft skill candidate for a missing capability.

        Args:
            prompt: Missing-capability description.

        Returns:
            Draft skill candidate response.
        """
        return await backend_tool_gateway.alexandria_request_skill_acquisition(
            api_client, prompt
        )

    @server.tool(name="alexandria_submit_skill_candidate")
    async def _tool_submit_skill_candidate(
        title: str,
        purpose: str,
        content: str,
        summary: str | None = None,
    ) -> JSONValue:
        """Submit a Hermes-authored skill candidate.

        Args:
            title: Candidate title.
            purpose: Candidate purpose.
            content: Candidate Markdown content.
            summary: Optional candidate summary.

        Returns:
            Stored skill response.
        """
        return await backend_tool_gateway.alexandria_submit_skill_candidate(
            api_client, title, purpose, content, summary
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
