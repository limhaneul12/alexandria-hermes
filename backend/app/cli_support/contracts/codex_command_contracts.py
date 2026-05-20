"""Codex integration CLI command contracts."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True, kw_only=True)
class CodexMcpInstallCommand:
    """Parameters for installing Codex MCP configuration."""

    codex_home: str | None
    api_url: str | None
    operator_api_key: str | None
    dry_run: bool
    overwrite: bool
