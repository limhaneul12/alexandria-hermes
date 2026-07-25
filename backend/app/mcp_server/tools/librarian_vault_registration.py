"""Register librarian review and vault maintenance MCP tools."""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from app.mcp_server import backend_tool_gateway
from app.mcp_server.backend_api_client import AlexandriaApiClient
from app.shared.types.extra_types import JSONValue


def register_librarian_vault_tools(
    server: FastMCP, api_client: AlexandriaApiClient
) -> None:
    """Register librarian review and vault maintenance MCP tools.

    Args:
        server: FastMCP server receiving tool registrations.
        api_client: Backend HTTP API client used by tool callbacks.
    """

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
