"""Register librarian OAuth MCP tools."""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from app.mcp_server.backend_api_client import AlexandriaApiClient
from app.mcp_server.tools.oauth_backend_gateway import (
    alexandria_librarian_oauth_poll,
    alexandria_librarian_oauth_refresh,
    alexandria_librarian_oauth_start,
    alexandria_librarian_oauth_status,
)
from app.shared.types.extra_types import JSONValue


def register_librarian_oauth_tools(
    server: FastMCP, api_client: AlexandriaApiClient
) -> None:
    """Register librarian OAuth MCP tools.

    Args:
        server: FastMCP server receiving tool registrations.
        api_client: Backend HTTP API client used by tool callbacks.
    """

    @server.tool(name="alexandria_librarian_oauth_start")
    async def _tool_librarian_oauth_start(provider_id: str) -> JSONValue:
        """Start OAuth device authorization for a librarian provider.

        Args:
            provider_id: Librarian provider id.

        Returns:
            Public OAuth start response with secret codes removed.
        """
        return await alexandria_librarian_oauth_start(api_client, provider_id)

    @server.tool(name="alexandria_librarian_oauth_poll")
    async def _tool_librarian_oauth_poll(provider_id: str) -> JSONValue:
        """Poll OAuth device authorization for a librarian provider.

        Args:
            provider_id: Librarian provider id.

        Returns:
            Public OAuth status response without token material.
        """
        return await alexandria_librarian_oauth_poll(api_client, provider_id)

    @server.tool(name="alexandria_librarian_oauth_status")
    async def _tool_librarian_oauth_status(provider_id: str) -> JSONValue:
        """Read OAuth connection status for a librarian provider.

        Args:
            provider_id: Librarian provider id.

        Returns:
            Public OAuth status response without token material.
        """
        return await alexandria_librarian_oauth_status(api_client, provider_id)

    @server.tool(name="alexandria_librarian_oauth_refresh")
    async def _tool_librarian_oauth_refresh(provider_id: str) -> JSONValue:
        """Refresh OAuth tokens for a librarian provider when needed.

        Args:
            provider_id: Librarian provider id.

        Returns:
            Public OAuth status response without token material.
        """
        return await alexandria_librarian_oauth_refresh(api_client, provider_id)
