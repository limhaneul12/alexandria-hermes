"""Pydantic schemas for MCP OAuth protected-resource metadata."""

from __future__ import annotations

from app.shared.schemas.common_schemas import StrictSchemaModel


class McpProtectedResourceMetadata(StrictSchemaModel):
    """OAuth protected-resource metadata exposed for ChatGPT MCP linking."""

    resource: str
    authorization_servers: tuple[str, ...]
    scopes_supported: tuple[str, ...]
    bearer_methods_supported: tuple[str, ...] = ("header",)
    resource_documentation: str | None = None
