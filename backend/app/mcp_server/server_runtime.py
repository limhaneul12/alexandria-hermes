"""Alexandria-Hermes MCP server bootstrap."""

from __future__ import annotations

import argparse
from collections.abc import Sequence

from mcp.server.fastmcp import FastMCP

from app.mcp_server.backend_api_client import AlexandriaApiClient, AlexandriaApiSettings
from app.mcp_server.tools.context_lifecycle_registration import (
    register_context_lifecycle_tools,
)
from app.mcp_server.tools.context_recall_registration import (
    register_context_recall_tools,
)
from app.mcp_server.tools.librarian_registration import register_librarian_tools
from app.mcp_server.tools.librarian_vault_registration import (
    register_librarian_vault_tools,
)
from app.mcp_server.tools.memory_compact_registration import (
    register_memory_compact_tools,
)
from app.mcp_server.tools.memory_reconciliation_registration import (
    register_memory_reconciliation_tools,
)
from app.mcp_server.tools.oauth_registration import register_librarian_oauth_tools
from app.mcp_server.tools.obsidian_note_registration import register_obsidian_note_tools
from app.mcp_server.tools.operations_registration import register_operations_tools
from app.mcp_server.type_validate.transport_contracts import McpTransport

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
    register_memory_reconciliation_tools(server, api_client)
    register_context_recall_tools(server, api_client)
    register_memory_compact_tools(server, api_client)
    register_librarian_tools(server, api_client)
    register_librarian_oauth_tools(server, api_client)
    register_context_lifecycle_tools(server, api_client)
    register_operations_tools(server, api_client)
    register_librarian_vault_tools(server, api_client)
    register_obsidian_note_tools(server, api_client)
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
