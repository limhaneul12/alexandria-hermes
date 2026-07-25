"""Register Memory Compact MCP tools."""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from app.mcp_server import backend_tool_gateway
from app.mcp_server.backend_api_client import AlexandriaApiClient
from app.memory.domain.event_enum.memory_compact_enums import (
    MemoryCompactStatus,
)
from app.shared.types.extra_types import JSONValue


def register_memory_compact_tools(
    server: FastMCP, api_client: AlexandriaApiClient
) -> None:
    """Register Memory Compact MCP tools.

    Args:
        server: FastMCP server receiving tool registrations.
        api_client: Backend HTTP API client used by tool callbacks.
    """

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
