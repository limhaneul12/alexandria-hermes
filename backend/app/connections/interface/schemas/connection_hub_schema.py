"""Public connection-hub configuration schema."""

from __future__ import annotations

from app.mcp_server.type_validate.auth_contracts import McpAuthMode
from app.shared.schemas.common_schemas import StrictSchemaModel
from app.shared.schemas.datetime_schemas import AwareTimestamp


class ConnectionHubStatusResponse(StrictSchemaModel):
    """Safe runtime details needed by the browser connection page."""

    app_env: str
    mcp_auth_mode: McpAuthMode
    mcp_endpoint: str
    mcp_oauth_enabled: bool
    mcp_oauth_issuer: str | None
    local_only: bool


class McpPairingCodeResponse(StrictSchemaModel):
    """Single-use MCP approval code shown once to the local operator."""

    code: str
    expires_at: AwareTimestamp
