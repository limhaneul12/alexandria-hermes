"""Behavior tests for Hermes awareness source assets."""

from __future__ import annotations

import io
from pathlib import Path

from app.cli import run
from app.cli_support.support.hermes.install.asset_sources import (
    load_alexandria_prompt_sources,
    load_alexandria_skill_source,
)
from app.shared.serialization.orjson_codec import loads_json


def test_alexandria_awareness_skill_source_teaches_policy_and_local_first() -> None:
    """Source skill gives Hermes the operating contract after installation."""
    skill = load_alexandria_skill_source()

    assert "name: alexandria-library" in skill
    assert "local/current context" in skill
    assert "enabled: false" in skill
    assert "status/diagnostics" in skill
    assert "explicit user request" in skill


def test_alexandria_prompt_sources_include_operating_loop_and_fallbacks() -> None:
    """Prompt source bundle includes operating-loop and CLI/MCP fallback guidance."""
    prompts = load_alexandria_prompt_sources()

    assert "alexandria-operating-loop.md" in prompts
    assert "use-alexandria-library.md" in prompts
    all_prompt_text = "\n".join(prompts.values())
    assert "mcp_alexandria" in all_prompt_text
    assert "alexandria-hermes context recall" in all_prompt_text
    assert "enabled: false" in all_prompt_text


def test_setup_can_plan_hermes_awareness_asset_install(tmp_path: Path) -> None:
    """Setup reports Hermes skill/prompt/policy assets when requested."""
    hermes_home = tmp_path / "hermes"
    hermes_home.mkdir()
    stdout = io.StringIO()

    exit_code = run(
        [
            "--json",
            "setup",
            "--mode",
            "guidebook-only",
            "--hermes-home",
            str(hermes_home),
            "--install-hermes-assets",
            "--dry-run",
        ],
        stdout=stdout,
    )

    payload = loads_json(stdout.getvalue())
    planned_files = payload["hermes_assets"]["planned_files"]
    assert exit_code == 0
    assert "skills/alexandria-hermes/alexandria-library/SKILL.md" in planned_files
    assert "alexandria-hermes/policy.yaml" in planned_files
    assert payload["hermes_assets_planned"] is True
