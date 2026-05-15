"""Hermes integration file planning and installation helpers."""

from __future__ import annotations

import shutil
from pathlib import Path

from app.cli_support.contracts.command_contracts import (
    HermesBundleCommand,
    HermesSyncCommand,
)
from app.cli_support.contracts.runtime_contracts import (
    CommandContext,
    HermesInstallFile,
)
from app.cli_support.hermes.home_resolution import (
    hermes_api_url,
    resolve_hermes_home,
    validate_hermes_home,
)
from app.cli_support.schemas.hermes_integration_schemas import (
    HermesBundleInstallationResult,
    McpConfiguration,
    McpServerEnvironment,
    McpServerLaunch,
)
from app.cli_support.serialization.json_payloads import schema_payload
from app.mcp_server.mcp_protocol_enums import (
    McpExecutable,
    McpLaunchArgument,
    McpServerKey,
)
from app.shared.serialization.orjson_codec import dumps_pretty_json
from app.shared.types.extra_types import JSONObject


def install_hermes_bundle(
    command: HermesBundleCommand | HermesSyncCommand,
    context: CommandContext,
    include_prompts: bool,
    include_mcp: bool,
) -> JSONObject:
    """Install or preview Hermes integration files.

    Args:
        command: CLI command contract with Hermes paths and backend auth options.
        context: Runtime context containing backend defaults and output streams.
        include_prompts: Whether prompt instruction files should be planned.
        include_mcp: Whether the MCP config file should be planned.

    Returns:
        JSON-compatible CLI result with planned and written file paths.
    """
    resolved = resolve_hermes_home(command.hermes_home, require_source=False)
    validate_hermes_home(resolved.path)
    api_url = hermes_api_url(command, context)
    api_token = command.api_token
    files = hermes_install_files(
        hermes_home=resolved.path,
        api_url=api_url,
        api_token=api_token,
        include_prompts=include_prompts,
        include_mcp=include_mcp,
    )
    dry_run = bool(command.dry_run)
    written, skipped, backups = apply_hermes_files(
        hermes_home=resolved.path,
        files=files,
        dry_run=dry_run,
        overwrite=bool(command.overwrite),
    )
    planned_files = tuple(file.relative_path for file in files)
    result = HermesBundleInstallationResult(
        hermes_home=str(resolved.path),
        source=resolved.source,
        dry_run=dry_run,
        planned_files=planned_files,
        written=tuple(written),
        skipped=tuple(skipped),
        backups=tuple(backups),
        mcp_config=build_mcp_configuration(
            hermes_home=resolved.path,
            api_url=api_url,
            api_token=redacted_token(api_token),
        ),
    )
    payload = schema_payload(result, by_alias=True)
    return payload


def apply_hermes_files(
    hermes_home: Path,
    files: list[HermesInstallFile],
    dry_run: bool,
    overwrite: bool,
) -> tuple[list[str], list[str], list[str]]:
    """Write or preview planned Hermes integration files.

    Args:
        hermes_home: Target Hermes home directory.
        files: Planned files with relative paths and content.
        dry_run: Whether writes should be previewed without filesystem changes.
        overwrite: Whether existing files should be replaced with backups.

    Returns:
        Tuple of written, skipped, and backup relative paths.
    """
    written: list[str] = []
    skipped: list[str] = []
    backups: list[str] = []
    for file in files:
        target = hermes_home / file.relative_path
        if target.exists() and not overwrite:
            skipped.append(file.relative_path)
            continue
        if dry_run:
            written.append(file.relative_path)
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists():
            backup = target.with_name(f"{target.name}.bak")
            shutil.copyfile(target, backup)
            backups.append(str(backup.relative_to(hermes_home)))
        target.write_text(file.content, encoding="utf-8")
        written.append(file.relative_path)
    return written, skipped, backups


def hermes_install_files(
    hermes_home: Path,
    api_url: str,
    api_token: str,
    include_prompts: bool,
    include_mcp: bool,
) -> list[HermesInstallFile]:
    """Build the Hermes integration file plan.

    Args:
        hermes_home: Target Hermes home directory.
        api_url: Backend API URL written to generated config.
        api_token: Backend API token written to generated config.
        include_prompts: Whether prompt instruction files should be included.
        include_mcp: Whether the MCP config file should be included.

    Returns:
        Planned files to write under the Hermes home directory.
    """
    files: list[HermesInstallFile] = []
    if include_prompts:
        files.extend(hermes_prompt_files())
    if include_mcp:
        files.append(
            HermesInstallFile(
                relative_path="alexandria-hermes/mcp-config.json",
                content=dumps_pretty_json(
                    schema_payload(
                        build_mcp_configuration(
                            hermes_home=hermes_home,
                            api_url=api_url,
                            api_token=api_token,
                        ),
                        by_alias=True,
                    )
                ).decode("utf-8"),
            )
        )
    return files


def hermes_prompt_files() -> list[HermesInstallFile]:
    """Build static Hermes instruction files.

    Args:
        None.

    Returns:
        Prompt and policy files used by Hermes to discover Alexandria-Hermes.
    """
    prompts = {
        "capture-context.md": "# Capture Context\n\nCapture durable project state in Alexandria-Hermes before handoff, compaction, or risky edits.\n",
        "prepare-compact.md": "# Prepare Compact\n\nSummarize current goal, completed work, in-progress work, decisions, risks, and next actions before context compaction.\n",
        "save-decision.md": "# Save Decision\n\nSave architectural and workflow decisions with evidence, rejected alternatives, and future directives.\n",
        "save-bug-root-cause.md": "# Save Bug Root Cause\n\nSave verified bug root causes, reproduction evidence, fixed files, and regression tests.\n",
        "save-context.md": "# Save Context\n\nSave important project memory when a decision, bug root cause, reusable workflow, or handoff appears.\n",
        "use-alexandria-library.md": "# Use Alexandria-Hermes Library\n\nCheck local Hermes skills first. If none fit, search Alexandria-Hermes. Use matching skills/prompts and record usage.\n",
        "request-skill-acquisition.md": "# Request Skill Acquisition\n\nWhen a capability is missing, describe the task, check Alexandria, research official docs when possible, and submit a candidate before delegating research.\n",
        "submit-skill-candidate.md": "# Submit Skill Candidate\n\nInclude title, purpose, content, evidence/source URLs, tags, and source_agent = Hermes when submitting a candidate.\n",
    }
    files = [
        HermesInstallFile(
            relative_path="skills/alexandria-hermes/alexandria-library/SKILL.md",
            content=(
                "# Alexandria-Hermes Library\n\n"
                "Use Alexandria-Hermes as a fallback library for skills, prompts, "
                "Context Vault recall, and skill acquisition requests.\n"
            ),
        ),
        HermesInstallFile(
            relative_path="alexandria-hermes/README.md",
            content=(
                "# Alexandria-Hermes for Hermes\n\n"
                "These files teach Hermes to use Alexandria-Hermes safely through "
                "the CLI and MCP server.\n"
            ),
        ),
        HermesInstallFile(
            relative_path="alexandria-hermes/alexandria-rules.md",
            content=(
                "# Alexandria Rules\n\n"
                "Prefer local Hermes assets, then Alexandria search, then Hermes "
                "self-acquisition, with librarian research as fallback.\n"
            ),
        ),
        HermesInstallFile(
            relative_path="alexandria-hermes/librarian-policy.md",
            content=(
                "# Librarian Policy\n\n"
                "Ask the librarian only when local and Alexandria assets are not "
                "sufficient and self-acquisition cannot produce reliable output.\n"
            ),
        ),
        HermesInstallFile(
            relative_path="alexandria-hermes/skill-acquisition.md",
            content=(
                "# Skill Acquisition\n\n"
                "Research official sources, draft a reusable skill candidate, lint "
                "it, and submit it to Alexandria-Hermes.\n"
            ),
        ),
        HermesInstallFile(
            relative_path="alexandria-hermes/context-policy.md",
            content=(
                "# Context Policy\n\n"
                "Save durable handoffs, decisions, bug root causes, and reusable "
                "workflow memory. Do not save high-risk secrets raw.\n"
            ),
        ),
    ]
    files.extend(
        HermesInstallFile(
            relative_path=f"alexandria-hermes/prompts/{name}",
            content=content,
        )
        for name, content in prompts.items()
    )
    return files


def build_mcp_configuration(
    hermes_home: Path,
    api_url: str,
    api_token: str,
) -> McpConfiguration:
    """Build the typed MCP configuration contract for Hermes.

    Args:
        hermes_home: Hermes home path exposed to the MCP server process.
        api_url: Backend API URL exposed to the MCP server process.
        api_token: Backend API token exposed to the MCP server process.

    Returns:
        Typed MCP configuration payload.
    """
    launch = McpServerLaunch(
        command=McpExecutable.ALEXANDRIA_HERMES,
        args=(McpLaunchArgument.MCP, McpLaunchArgument.SERVE),
        env=McpServerEnvironment(
            alexandria_api_url=api_url,
            alexandria_api_token=api_token,
            hermes_home=str(hermes_home),
        ),
    )
    config = McpConfiguration(mcp_servers={McpServerKey.ALEXANDRIA: launch})
    return config


def redacted_token(api_token: str) -> str:
    """Return a safe token value for command output.

    Args:
        api_token: Raw API token from flags or environment.

    Returns:
        Redacted placeholder for non-empty tokens; empty string otherwise.
    """
    redacted = "<REDACTED>" if api_token != "" else ""
    return redacted
