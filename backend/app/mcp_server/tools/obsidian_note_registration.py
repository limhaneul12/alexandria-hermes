"""Register Obsidian note and graph MCP tools."""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from app.mcp_server.backend_api_client import AlexandriaApiClient
from app.mcp_server.tools.backend_gateway_policy import DEFAULT_CONTEXT_SEARCH_LIMIT
from app.mcp_server.tools.obsidian_backend_gateway import (
    alexandria_ask_obsidian_librarian,
    alexandria_get_related_notes,
    alexandria_read_note,
    alexandria_save_note,
)
from app.shared.types.extra_types import JSONValue


def register_obsidian_note_tools(
    server: FastMCP, api_client: AlexandriaApiClient
) -> None:
    """Register Obsidian note and graph MCP tools.

    Args:
        server: FastMCP server receiving tool registrations.
        api_client: Backend HTTP API client used by tool callbacks.
    """

    @server.tool(name="alexandria_read_note")
    async def _tool_read_note(
        note_id: str | None = None,
        path: str | None = None,
    ) -> JSONValue:
        """Read one Alexandria-managed Obsidian note by id or path."""
        return await alexandria_read_note(api_client, note_id, path)

    @server.tool(name="alexandria_get_related_notes")
    async def _tool_get_related_notes(
        note_id: str | None = None,
        path: str | None = None,
        limit: int = DEFAULT_CONTEXT_SEARCH_LIMIT,
    ) -> JSONValue:
        """Read graph-related Obsidian notes by id or path."""
        return await alexandria_get_related_notes(api_client, note_id, path, limit)

    @server.tool(name="alexandria_save_note")
    async def _tool_save_note(
        title: str,
        body: str,
        alexandria_type: str,
        note_id: str | None = None,
        path: str | None = None,
        project: str | None = None,
        tags: list[str] | str | None = None,
        status: str = "active",
        source: str = "mcp",
        frontmatter: dict[str, JSONValue] | None = None,
    ) -> JSONValue:
        """Save one Alexandria-managed Obsidian Markdown note."""
        return await alexandria_save_note(
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
        return await alexandria_ask_obsidian_librarian(
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
