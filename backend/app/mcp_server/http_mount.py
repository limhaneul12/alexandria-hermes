"""ASGI mount helpers for the Alexandria-Hermes HTTP MCP endpoint."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Receive, Scope, Send

from app.mcp_server.backend_api_client import AlexandriaApiClient
from app.mcp_server.http_auth_gate import McpHttpAuthGate
from app.mcp_server.server_runtime import DEFAULT_MCP_TRANSPORT_HOST, build_mcp_server

MCP_HTTP_MOUNT_PATH = "/mcp"
_MOUNTED_STREAMABLE_HTTP_PATH = "/"


class McpHttpMount:
    """Restart-safe ASGI delegate for the mounted FastMCP HTTP app."""

    def __init__(self, auth_gate: McpHttpAuthGate) -> None:
        """Create the guarded MCP mount delegate.

        Args:
            auth_gate: Public MCP request authorization gate.

        Returns:
            None.
        """
        self._auth_gate = auth_gate
        self._app: ASGIApp | None = None

    def set_app(self, app: ASGIApp | None) -> None:
        """Set the currently running FastMCP ASGI app.

        Args:
            app: Mounted app for the current FastAPI lifespan, or None at shutdown.

        Returns:
            None.
        """
        self._app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        """Handle an ASGI request by delegating to the active MCP app.

        Args:
            scope: ASGI request scope.
            receive: ASGI receive callable.
            send: ASGI send callable.

        Returns:
            None.
        """
        auth_result = await self._auth_gate.authorize(scope)
        if not auth_result.allowed:
            response = JSONResponse(
                {"detail": auth_result.detail},
                status_code=auth_result.status_code,
                headers=dict(auth_result.headers),
            )
            await response(scope, receive, send)
            return
        if self._app is None:
            response = JSONResponse({"detail": "MCP server is not running"}, 503)
            await response(scope, receive, send)
            return
        await self._app(scope, receive, send)


@asynccontextmanager
async def mcp_streamable_http_lifespan(
    client: AlexandriaApiClient | None = None,
    transport_host: str = DEFAULT_MCP_TRANSPORT_HOST,
) -> AsyncIterator[ASGIApp]:
    """Run one restart-safe FastMCP Streamable HTTP app lifespan.

    Args:
        client: Optional backend API client for tests.
        transport_host: Host value used by FastMCP transport security.

    Yields:
        ASGIApp: Active FastMCP Streamable HTTP app.
    """
    server = build_mcp_server(
        client=client,
        streamable_http_path=_MOUNTED_STREAMABLE_HTTP_PATH,
        transport_host=transport_host,
    )
    mcp_app = server.streamable_http_app()
    async with mcp_app.router.lifespan_context(mcp_app):
        yield mcp_app
