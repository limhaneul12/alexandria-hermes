"""Librarian OAuth MCP HTTP gateway functions."""

from __future__ import annotations

from app.mcp_server.backend_api_client import AlexandriaApiClient
from app.mcp_server.tools.backend_gateway_policy import (
    _path_segment,
)
from app.shared.types.extra_types import JSONValue
from app.shared.utils.oauth_redaction import without_oauth_sensitive_fields


async def alexandria_librarian_oauth_start(
    client: AlexandriaApiClient,
    provider_id: str,
) -> JSONValue:
    """Start OAuth device authorization for a librarian provider.

    Args:
        client: Backend HTTP client.
        provider_id: Librarian provider id.

    Returns:
        Sanitized OAuth start response with codes and credential material removed.
    """
    response = await client.post(
        f"/settings/connections/{_path_segment(provider_id)}/oauth/start", {}
    )
    return without_oauth_sensitive_fields(response)


async def alexandria_librarian_oauth_poll(
    client: AlexandriaApiClient,
    provider_id: str,
) -> JSONValue:
    """Poll OAuth device authorization for a librarian provider.

    Args:
        client: Backend HTTP client.
        provider_id: Librarian provider id.

    Returns:
        Sanitized public OAuth status response.
    """
    response = await client.post(
        f"/settings/connections/{_path_segment(provider_id)}/oauth/poll", {}
    )
    return without_oauth_sensitive_fields(response)


async def alexandria_librarian_oauth_status(
    client: AlexandriaApiClient,
    provider_id: str,
) -> JSONValue:
    """Read public OAuth connection status for a librarian provider.

    Args:
        client: Backend HTTP client.
        provider_id: Librarian provider id.

    Returns:
        Sanitized public OAuth status response.
    """
    response = await client.get(
        f"/settings/connections/{_path_segment(provider_id)}/oauth/status"
    )
    return without_oauth_sensitive_fields(response)


async def alexandria_librarian_oauth_refresh(
    client: AlexandriaApiClient,
    provider_id: str,
) -> JSONValue:
    """Refresh OAuth tokens for a librarian provider when needed.

    Args:
        client: Backend HTTP client.
        provider_id: Librarian provider id.

    Returns:
        Sanitized public OAuth status response.
    """
    response = await client.post(
        f"/settings/connections/{_path_segment(provider_id)}/oauth/refresh", {}
    )
    return without_oauth_sensitive_fields(response)
