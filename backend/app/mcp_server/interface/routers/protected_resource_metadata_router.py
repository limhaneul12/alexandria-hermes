"""Routes for MCP OAuth protected-resource metadata discovery."""

from __future__ import annotations

from app.mcp_server.protected_resource_metadata import protected_resource_metadata
from app.mcp_server.type_validate.auth_contracts import (
    MCP_OAUTH_PROTECTED_RESOURCE_PATH,
)
from app.platform.config.app_config import AppConfig
from app.shared.types.extra_types import JSONObject
from fastapi import APIRouter, Request

router = APIRouter(tags=["mcp-oauth"])


@router.get(MCP_OAUTH_PROTECTED_RESOURCE_PATH, response_model=None)
def read_mcp_protected_resource_metadata(request: Request) -> JSONObject:
    """Return OAuth protected-resource metadata for ChatGPT MCP clients.

    Args:
        request: Incoming request used to infer the public resource origin.

    Returns:
        OAuth protected-resource metadata payload.
    """
    config = getattr(request.app.state, "app_config", AppConfig())
    return protected_resource_metadata(request, config)
