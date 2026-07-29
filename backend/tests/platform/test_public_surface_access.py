"""Public-host access boundaries for the locally operated backend."""

from __future__ import annotations

from app.main import app
from fastapi.testclient import TestClient


def test_public_host_exposes_only_mcp_oauth_protocol_routes() -> None:
    """A tunnel host must not expose operator UI or backend management APIs."""
    with TestClient(app, base_url="https://alexandria.example") as client:
        blocked = {
            "/": client.get("/"),
            "/connect": client.get("/connect"),
            "/connect/status": client.get("/connect/status"),
            "/settings/connections": client.get("/settings/connections"),
            "/operations/readiness": client.get("/operations/readiness"),
            "/docs": client.get("/docs"),
        }
        live = client.get("/health/live")
        authorization_metadata = client.get("/.well-known/oauth-authorization-server")
        resource_metadata = client.get("/.well-known/oauth-protected-resource/mcp")
        unauthenticated_mcp = client.get("/mcp")

    assert {path: response.status_code for path, response in blocked.items()} == {
        "/": 403,
        "/connect": 403,
        "/connect/status": 403,
        "/settings/connections": 403,
        "/operations/readiness": 403,
        "/docs": 403,
    }
    assert all(
        response.headers["cache-control"] == "no-store" for response in blocked.values()
    )
    assert live.status_code == 200
    assert authorization_metadata.status_code == 200
    assert resource_metadata.status_code == 200
    assert unauthenticated_mcp.status_code == 401


def test_localhost_retains_operator_surface_access() -> None:
    """The local operator must retain the connection hub and management APIs."""
    with TestClient(app) as client:
        hub = client.get("/connect")
        status = client.get("/connect/status")
        connections = client.get("/settings/connections")
        readiness = client.get("/operations/readiness")

    assert hub.status_code == 200
    assert status.status_code == 200
    assert connections.status_code == 200
    assert readiness.status_code == 200
