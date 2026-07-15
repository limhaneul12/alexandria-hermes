"""MCP/librarian Makefile boundary tests."""

from __future__ import annotations

from pathlib import Path

OPERATIONAL_TARGETS = (
    "mcp-smoke-tools",
    "librarian-check",
    "librarian-check-summary",
    "librarian-check-refresh",
    "librarian-check-refresh-summary",
    "librarian-preflight",
    "librarian-preflight-refresh",
    "librarian-review-queue",
    "librarian-review-queue-summary",
    "librarian-review-plan",
    "librarian-review-apply",
)


def test_makefile_keeps_only_build_and_ci_targets() -> None:
    """Makefile should stay focused on install, smoke, and CI workflows."""
    makefile = Path(__file__).resolve().parents[2] / "Makefile"
    text = makefile.read_text()

    assert (
        ".PHONY: install-local format_check type_checking cli_smoke guardrails test ci"
        in text
    )
    assert "ci: format_check type_checking cli_smoke guardrails test" in text
    assert "cli_smoke: install-local" in text
    assert "uv sync --no-editable --reinstall-package alexandria-hermes" in text
    assert "uv run --no-editable alexandria-hermes --help >/dev/null" in text
    assert "uv run --no-editable alex-hermes --help >/dev/null" in text
    assert "LOAD_LOCAL_ENV" not in text
    assert "PROJECT ?=" not in text
    assert "REVIEW_LIMIT ?=" not in text
    for target in OPERATIONAL_TARGETS:
        assert f"\n{target}:" not in text


def test_package_cli_declares_direct_typer_dependency() -> None:
    """Typer CLI package should not rely on transitive dependency exposure."""
    pyproject = Path(__file__).resolve().parents[2] / "pyproject.toml"
    text = pyproject.read_text()

    assert '"typer>=0.25.1,<1.0.0"' in text


def test_package_cli_mcp_modules_are_explicit_packages() -> None:
    """Installed CLI should not depend on implicit namespace package discovery."""
    backend_root = Path(__file__).resolve().parents[2]

    assert (backend_root / "app" / "__init__.py").is_file()
    cli_root = backend_root / "app" / "cli"
    assert (cli_root / "__init__.py").is_file()
    assert (cli_root / "main.py").is_file()
    assert (cli_root / "mcp_server_commands.py").is_file()
    assert (cli_root / "librarian_workflow_commands.py").is_file()
    assert (cli_root / "librarian_readiness_commands.py").is_file()
    assert (cli_root / "librarian_review_commands.py").is_file()
    assert (cli_root / "librarian_command_context.py").is_file()
    assert (cli_root / "type_validate" / "command_options.py").is_file()
    assert (cli_root / "type_validate" / "librarian_payload_schemas.py").is_file()
    assert not (cli_root / "mcp.py").exists()
    assert not (cli_root / "librarian.py").exists()
    assert not (cli_root / "options.py").exists()
    assert not (cli_root / "librarian_payloads.py").exists()
    assert (backend_root / "app" / "mcp_server" / "__init__.py").is_file()
    assert (
        backend_root / "app" / "mcp_server" / "type_validate" / "transport_contracts.py"
    ).is_file()
    assert (backend_root / "app" / "mcp_server" / "tools" / "__init__.py").is_file()
    assert (backend_root / "app" / "mcp_server" / "server_runtime.py").is_file()
    assert (backend_root / "app" / "mcp_server" / "backend_tool_gateway.py").is_file()
