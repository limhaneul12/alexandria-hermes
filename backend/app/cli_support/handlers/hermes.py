"""Handlers for Hermes integration CLI commands."""

from __future__ import annotations

import os

from app.cli_support.contracts.command_contracts import (
    HermesBundleCommand,
    HermesConfigureCommand,
    HermesDoctorCommand,
    HermesInstallCommand,
    HermesOnboardCommand,
    HermesPolicyCommand,
    HermesScanCommand,
    HermesSyncCommand,
)
from app.cli_support.contracts.runtime_contracts import CommandContext
from app.cli_support.hermes.home_resolution import (
    hermes_api_url,
    hermes_config_path,
    resolve_hermes_home,
    scan_base_path,
    scan_hermes_files,
    validate_hermes_home,
)
from app.cli_support.hermes.integration_files import (
    build_mcp_configuration,
    install_hermes_bundle,
)
from app.cli_support.hermes.policy_files import read_policy, write_policy
from app.cli_support.presentation.output_renderers import print_hermes_payload
from app.cli_support.schemas.hermes_integration_schemas import (
    HermesConfigurationResult,
    HermesDoctorResult,
    HermesLocalConfiguration,
    HermesScanResult,
)
from app.cli_support.serialization.json_payloads import schema_payload
from app.shared.serialization.orjson_codec import dumps_pretty_json


def handle_hermes_configure(
    command: HermesConfigureCommand,
    context: CommandContext,
) -> int:
    """Save Hermes integration configuration.

    Args:
        command: CLI command contract with Hermes path and API URL values.
        context: Runtime context containing output streams and default API URL.

    Returns:
        Process-style exit code.
    """
    resolved = resolve_hermes_home(command.hermes_home, require_source=False)
    validate_hermes_home(resolved.path)
    api_url = hermes_api_url(command, context)
    local_config = HermesLocalConfiguration(
        hermes_home=str(resolved.path),
        api_url=api_url,
        source=resolved.source,
    )
    dry_run = bool(command.dry_run)
    if not dry_run:
        config_path = hermes_config_path()
        config_path.parent.mkdir(parents=True, exist_ok=True)
        config_path.write_text(
            dumps_pretty_json(schema_payload(local_config, by_alias=True)).decode(
                "utf-8"
            ),
            encoding="utf-8",
        )
    result = HermesConfigurationResult(
        hermes_home=str(resolved.path),
        config_path=str(hermes_config_path()),
        dry_run=dry_run,
        mcp_config=build_mcp_configuration(
            hermes_home=resolved.path,
            api_url=api_url,
            operator_api_key=command.operator_api_key or "",
        ),
    )
    output = schema_payload(result, by_alias=True)
    print_hermes_payload(output, context)
    return 0


def handle_hermes_onboard(
    command: HermesOnboardCommand,
    context: CommandContext,
) -> int:
    """Install the default Hermes prompt and MCP integration bundle.

    Args:
        command: CLI command contract with install options.
        context: Runtime context containing output streams and default API URL.

    Returns:
        Process-style exit code.
    """
    install_prompts = bool(command.install_prompts)
    install_mcp = bool(command.install_mcp)
    if not install_prompts and not install_mcp:
        install_prompts = True
        install_mcp = True
    payload = install_hermes_bundle(
        command=command,
        context=context,
        include_prompts=install_prompts,
        include_mcp=install_mcp,
    )
    print_hermes_payload(payload, context)
    return 0


def handle_hermes_install(
    command: HermesInstallCommand,
    context: CommandContext,
) -> int:
    """Run the guided one-command Hermes installation flow.

    Args:
        command: CLI command contract with install options.
        context: Runtime context containing output streams and default API URL.

    Returns:
        Process-style exit code.
    """
    payload = install_hermes_bundle(
        command=command,
        context=context,
        include_prompts=True,
        include_mcp=True,
    )
    print_hermes_payload(payload, context)
    return 0


def handle_hermes_install_prompts(
    command: HermesBundleCommand,
    context: CommandContext,
) -> int:
    """Install Hermes prompt integration files.

    Args:
        command: CLI command contract with install options.
        context: Runtime context containing output streams and default API URL.

    Returns:
        Process-style exit code.
    """
    payload = install_hermes_bundle(
        command=command,
        context=context,
        include_prompts=True,
        include_mcp=False,
    )
    print_hermes_payload(payload, context)
    return 0


def handle_hermes_install_mcp(
    command: HermesBundleCommand,
    context: CommandContext,
) -> int:
    """Install Hermes MCP integration config.

    Args:
        command: CLI command contract with install options.
        context: Runtime context containing output streams and default API URL.

    Returns:
        Process-style exit code.
    """
    payload = install_hermes_bundle(
        command=command,
        context=context,
        include_prompts=False,
        include_mcp=True,
    )
    print_hermes_payload(payload, context)
    return 0


def handle_hermes_doctor(
    command: HermesDoctorCommand,
    context: CommandContext,
) -> int:
    """Inspect Hermes integration state.

    Args:
        command: CLI command contract with diagnostic options.
        context: Runtime context containing output streams.

    Returns:
        Process-style exit code.
    """
    resolved = resolve_hermes_home(
        command.hermes_home,
        require_source=bool(command.require_home),
    )
    home = resolved.path
    exists = home.exists()
    writable = os.access(home, os.W_OK) if exists else False
    checks: dict[str, str] = {}
    restart_needed = False
    if command.deep:
        checks = {
            "backend_health": "CHECK_MANUALLY",
            "database_migration_head": "CHECK_MANUALLY",
            "prompt_item_type_constraint": "CHECK_MANUALLY",
            "hermes_home": "OK" if exists and home.is_dir() else "FAIL",
            "alexandria_prompt_assets": (
                "OK" if (home / "alexandria-hermes" / "prompts").exists() else "FAIL"
            ),
            "operating_loop_prompt": (
                "OK"
                if (
                    home
                    / "alexandria-hermes"
                    / "prompts"
                    / "alexandria-operating-loop.md"
                ).exists()
                else "FAIL"
            ),
            "mcp_snippet": (
                "OK"
                if (home / "alexandria-hermes" / "mcp-config.json").exists()
                else "FAIL"
            ),
            "policy_file": (
                "OK"
                if (home / "alexandria-hermes" / "policy.yaml").exists()
                else "FAIL"
            ),
            "hermes_native_mcp_servers_alexandria": "CHECK_MANUALLY",
            "hermes_mcp_test_alexandria": "CHECK_MANUALLY",
            "tool_discovery_count": "CHECK_MANUALLY",
        }
        restart_needed = True
    result = HermesDoctorResult(
        hermes_home=str(home),
        source=resolved.source,
        exists=exists,
        is_dir=home.is_dir(),
        writable=writable,
        alexandria_dir=(home / "alexandria-hermes").exists(),
        skill_installed=(
            home / "skills" / "alexandria-hermes" / "alexandria-library" / "SKILL.md"
        ).exists(),
        mcp_config_installed=(home / "alexandria-hermes" / "mcp-config.json").exists(),
        policy_installed=(home / "alexandria-hermes" / "policy.yaml").exists(),
        config_path=str(hermes_config_path()),
        mcp_config=build_mcp_configuration(
            hermes_home=home,
            api_url=hermes_api_url(command, context),
            operator_api_key=command.operator_api_key or "",
        ),
        deep=command.deep,
        checks=checks,
        restart_needed=restart_needed,
    )
    payload = schema_payload(result, by_alias=True)
    print_hermes_payload(payload, context)
    return 0


def handle_hermes_policy(
    command: HermesPolicyCommand,
    context: CommandContext,
) -> int:
    """Read or update the Hermes Alexandria usage policy.

    Args:
        command: CLI command contract with optional enabled state.
        context: Runtime context containing output streams.

    Returns:
        Process-style exit code.
    """
    resolved = resolve_hermes_home(command.hermes_home, require_source=False)
    validate_hermes_home(resolved.path)
    result = (
        read_policy(resolved.path)
        if command.enabled is None
        else write_policy(resolved.path, enabled=command.enabled)
    )
    payload = schema_payload(result, by_alias=True)
    print_hermes_payload(payload, context)
    return 0


def handle_hermes_scan(
    command: HermesScanCommand,
    context: CommandContext,
) -> int:
    """Scan Hermes integration files.

    Args:
        command: CLI command contract with scan path options.
        context: Runtime context containing output streams.

    Returns:
        Process-style exit code.
    """
    base = scan_base_path(command)
    rows = scan_hermes_files(base)
    result = HermesScanResult(path=str(base), files=rows)
    payload = schema_payload(result, by_alias=True)
    print_hermes_payload(payload, context)
    return 0


def handle_hermes_sync(
    command: HermesSyncCommand,
    context: CommandContext,
) -> int:
    """Sync Hermes prompt integration files.

    Args:
        command: CLI command contract with sync options.
        context: Runtime context containing output streams and default API URL.

    Returns:
        Process-style exit code.
    """
    payload = install_hermes_bundle(
        command=command,
        context=context,
        include_prompts=True,
        include_mcp=False,
    )
    print_hermes_payload(payload, context)
    return 0
