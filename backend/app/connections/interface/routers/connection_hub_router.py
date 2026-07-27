"""Server-rendered connection hub for local Alexandria operators."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Final

from app.connections.interface.schemas.connection_hub_schema import (
    ConnectionHubStatusResponse,
    McpPairingCodeResponse,
)
from app.container import ApplicationContainer
from app.mcp_server.local_oauth.provider import LocalMcpOAuthProvider
from app.mcp_server.type_validate.auth_contracts import McpAuthMode
from app.platform.config.app_config import AppConfig
from dependency_injector.wiring import Provide, inject
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import FileResponse

router = APIRouter(tags=["connection-hub"])

_INTERFACE_ROOT: Final[Path] = Path(__file__).resolve().parents[1]
_HUB_HTML: Final[Path] = _INTERFACE_ROOT / "templates" / "connection_hub.html"
_HUB_CSS: Final[Path] = _INTERFACE_ROOT / "static" / "connection_hub.css"
_HUB_JS: Final[Path] = _INTERFACE_ROOT / "static" / "connection_hub.js"
_PAGE_SECURITY_HEADERS: Final[dict[str, str]] = {
    "Cache-Control": "no-store",
    "Pragma": "no-cache",
    "Content-Security-Policy": (
        "default-src 'none'; script-src 'self'; style-src 'self'; "
        "connect-src 'self'; img-src 'self' data:; form-action 'self'; "
        "base-uri 'none'; frame-ancestors 'none'"
    ),
    "Referrer-Policy": "no-referrer",
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
}
_ASSET_HEADERS: Final[dict[str, str]] = {
    "Cache-Control": "no-store",
    "X-Content-Type-Options": "nosniff",
}


@router.get(
    "/connect",
    response_class=FileResponse,
    status_code=status.HTTP_200_OK,
    include_in_schema=False,
)
def connection_hub_page() -> FileResponse:
    """Return the local connection hub page.

    Returns:
        Hardened HTML file response.
    """
    return FileResponse(
        _HUB_HTML,
        media_type="text/html; charset=utf-8",
        headers=_PAGE_SECURITY_HEADERS,
    )


@router.get(
    "/connect/assets/connection-hub.css",
    response_class=FileResponse,
    status_code=status.HTTP_200_OK,
    include_in_schema=False,
)
def connection_hub_stylesheet() -> FileResponse:
    """Return the connection hub stylesheet.

    Returns:
        No-store CSS file response.
    """
    return FileResponse(
        _HUB_CSS,
        media_type="text/css; charset=utf-8",
        headers=_ASSET_HEADERS,
    )


@router.get(
    "/connect/assets/connection-hub.js",
    response_class=FileResponse,
    status_code=status.HTTP_200_OK,
    include_in_schema=False,
)
def connection_hub_script() -> FileResponse:
    """Return the connection hub browser controller.

    Returns:
        No-store JavaScript file response.
    """
    return FileResponse(
        _HUB_JS,
        media_type="text/javascript; charset=utf-8",
        headers=_ASSET_HEADERS,
    )


@router.get(
    "/connect/status",
    response_model=ConnectionHubStatusResponse,
    status_code=status.HTTP_200_OK,
    summary="Read connection hub runtime status",
)
def connection_hub_status(request: Request) -> ConnectionHubStatusResponse:
    """Return non-secret runtime details for the connection page.

    Args:
        request: Active FastAPI request.

    Returns:
        Public connection state without credentials.
    """
    config = getattr(request.app.state, "app_config", AppConfig())
    host = request.url.hostname or ""
    request_mcp_endpoint = str(request.base_url).rstrip("/") + "/mcp"
    return ConnectionHubStatusResponse(
        app_env=config.app_env,
        mcp_auth_mode=config.mcp_auth_mode,
        mcp_endpoint=config.mcp_oauth_resource or request_mcp_endpoint,
        mcp_oauth_enabled=config.mcp_auth_mode is McpAuthMode.LOCAL_OAUTH2,
        mcp_oauth_issuer=config.mcp_oauth_issuer,
        local_only=host in {"127.0.0.1", "localhost", "::1", "testserver"},
    )


@router.post(
    "/connect/mcp/pairing-code",
    response_model=McpPairingCodeResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a one-time MCP pairing code",
)
@inject
async def create_mcp_pairing_code(
    request: Request,
    configured_app: AppConfig = Depends(Provide[ApplicationContainer.app_config]),
) -> McpPairingCodeResponse:
    """Create one local-only, short-lived approval code for MCP OAuth.

    Args:
        request: Active FastAPI request.
        configured_app: Dependency-injected configuration fallback.

    Returns:
        One-time pairing code and expiration.
    """
    if request.url.hostname not in {"127.0.0.1", "localhost", "::1", "testserver"}:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="MCP pairing codes may only be created from localhost",
        )
    config = getattr(request.app.state, "app_config", configured_app)
    if config.mcp_auth_mode is not McpAuthMode.LOCAL_OAUTH2:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="MCP local OAuth is not enabled",
        )
    provider = getattr(request.app.state, "local_mcp_oauth_provider", None)
    if not isinstance(provider, LocalMcpOAuthProvider):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="MCP local OAuth is still starting",
        )
    pairing = await provider.create_pairing_code()
    return McpPairingCodeResponse(
        code=pairing.code,
        expires_at=datetime.fromtimestamp(pairing.expires_at, tz=UTC),
    )
