"""ASGI mount helpers for the Alexandria-Hermes HTTP MCP endpoint."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from hmac import compare_digest

from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Receive, Scope, Send

from app.mcp_server.backend_api_client import AlexandriaApiClient
from app.mcp_server.server_runtime import build_mcp_server
from app.platform.security.operator_api_key import OPERATOR_API_KEY_HEADER

MCP_HTTP_MOUNT_PATH = "/mcp"
_MOUNTED_STREAMABLE_HTTP_PATH = "/"


class McpHttpMount:
    """Restart-safe ASGI delegate for the mounted FastMCP HTTP app."""

    def __init__(self, *, expected_operator_api_key: str) -> None:
        """Create the guarded MCP mount delegate.

        Args:
            expected_operator_api_key: Operator key required at the MCP boundary.

        Returns:
            None.
        """
        self._expected_operator_api_key = expected_operator_api_key
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
        if scope["type"] == "http" and not self._has_valid_operator_key(scope):
            response = JSONResponse(
                {"detail": "Operator API key required"}, status_code=401
            )
            await response(scope, receive, send)
            return
        if self._app is None:
            response = JSONResponse({"detail": "MCP server is not running"}, 503)
            await response(scope, receive, send)
            return
        await self._app(scope, receive, send)

    def _has_valid_operator_key(self, scope: Scope) -> bool:
        headers = dict(scope.get("headers", []))
        raw_key = headers.get(OPERATOR_API_KEY_HEADER.lower().encode("ascii"))
        if raw_key is None:
            return False
        try:
            supplied_key = raw_key.decode("utf-8")
        except UnicodeDecodeError:
            return False
        return compare_digest(supplied_key, self._expected_operator_api_key)


@asynccontextmanager
async def mcp_streamable_http_lifespan(
    *, client: AlexandriaApiClient | None = None
) -> AsyncIterator[ASGIApp]:
    """Run one restart-safe FastMCP Streamable HTTP app lifespan.

    Args:
        client: Optional backend API client for tests.

    Yields:
        ASGIApp: Active FastMCP Streamable HTTP app.
    """
    server = build_mcp_server(
        client=client,
        streamable_http_path=_MOUNTED_STREAMABLE_HTTP_PATH,
    )
    mcp_app = server.streamable_http_app()
    async with mcp_app.router.lifespan_context(mcp_app):
        yield mcp_app
