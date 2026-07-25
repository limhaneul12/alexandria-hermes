"""Configuration invariants for Alexandria's local MCP OAuth mode."""

from __future__ import annotations

import pytest
from app.platform.config.app_config import AppConfig


def test_local_oauth_mode_requires_issuer_resource_and_approval_key() -> None:
    """Local token issuance must fail closed when public metadata is incomplete."""
    with pytest.raises(ValueError, match="MCP local OAuth mode requires"):
        AppConfig(_env_file=None, mcp_auth_mode="local_oauth2")


def test_local_oauth_mode_accepts_legacy_operator_key_environment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Existing local operator configuration should approve browser OAuth flows."""
    monkeypatch.setenv("ALEXANDRIA_OPERATOR_API_KEY", "o" * 32)

    config = AppConfig(
        _env_file=None,
        mcp_auth_mode="local_oauth2",
        mcp_oauth_issuer="http://127.0.0.1:8000",
        mcp_oauth_resource="http://127.0.0.1:8000/mcp",
    )

    assert config.mcp_local_approval_key_value() == "o" * 32
    assert config.mcp_local_oauth_default_scopes() == (
        "alexandria:mcp",
        "offline_access",
    )


def test_local_oauth_mode_rejects_remote_plain_http_and_cross_origin_resource() -> None:
    """Only localhost may use HTTP and issuer/resource must share an origin."""
    with pytest.raises(ValueError, match="HTTPS outside localhost"):
        AppConfig(
            _env_file=None,
            mcp_auth_mode="local_oauth2",
            mcp_oauth_issuer="http://mcp.example.com",
            mcp_oauth_resource="http://mcp.example.com/mcp",
            mcp_local_approval_key="o" * 32,
        )

    with pytest.raises(ValueError, match="share one origin"):
        AppConfig(
            _env_file=None,
            mcp_auth_mode="local_oauth2",
            mcp_oauth_issuer="https://auth.example.com",
            mcp_oauth_resource="https://mcp.example.com/mcp",
            mcp_local_approval_key="o" * 32,
        )


def test_local_oauth_mode_rejects_short_approval_key() -> None:
    """Browser approval credentials must resist online guessing."""
    with pytest.raises(ValueError, match="at least 24 characters"):
        AppConfig(
            _env_file=None,
            mcp_auth_mode="local_oauth2",
            mcp_oauth_issuer="https://mcp.example.com",
            mcp_oauth_resource="https://mcp.example.com/mcp",
            mcp_local_approval_key="too-short",
        )
