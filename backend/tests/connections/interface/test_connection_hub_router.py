"""Connection hub browser surface contracts."""

from __future__ import annotations

from app.main import app
from app.mcp_server.type_validate.auth_contracts import McpAuthMode
from app.platform.config.app_config import AppConfig
from fastapi.testclient import TestClient


def test_connection_hub_page_has_secure_external_assets() -> None:
    """Hub HTML should be browser-ready without inline script or secret fields."""
    with TestClient(app) as client:
        response = client.get("/connect")
        script = client.get("/connect/assets/connection-hub.js")
        stylesheet = client.get("/connect/assets/connection-hub.css")

    assert response.status_code == 200
    assert response.headers["cache-control"] == "no-store"
    assert "script-src 'self'" in response.headers["content-security-policy"]
    assert "<script src=" in response.text
    assert "<script>" not in response.text
    assert "operator_key" not in response.text
    assert "OpenAI Librarian" in response.text
    assert script.status_code == 200
    assert script.headers["content-type"].startswith("text/javascript")
    assert stylesheet.status_code == 200
    assert stylesheet.headers["content-type"].startswith("text/css")


def test_connection_hub_status_redacts_runtime_secrets() -> None:
    """Hub status should expose connection metadata but no credential material."""
    with TestClient(app) as client:
        response = client.get("/connect/status")

    assert response.status_code == 200
    payload = response.json()
    assert payload["mcp_endpoint"].endswith("/mcp")
    assert payload["local_only"] is True
    assert "token" not in response.text.lower()
    assert "approval_key" not in response.text.lower()


def test_connection_hub_status_prefers_configured_public_mcp_resource() -> None:
    """The copyable endpoint must use the public OAuth resource, not localhost."""
    with TestClient(app) as client:
        previous = getattr(app.state, "app_config", None)
        app.state.app_config = AppConfig(
            _env_file=None,
            mcp_auth_mode=McpAuthMode.LOCAL_OAUTH2,
            mcp_oauth_issuer="https://alexandria.example",
            mcp_oauth_resource="https://alexandria.example/mcp",
            mcp_local_approval_key="test-approval-key-24-chars",
        )
        try:
            response = client.get("/connect/status")
        finally:
            if previous is None:
                delattr(app.state, "app_config")
            else:
                app.state.app_config = previous

    assert response.status_code == 200
    assert response.json()["mcp_endpoint"] == "https://alexandria.example/mcp"
