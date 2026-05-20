"""Codex MCP configuration planning and installation helpers."""

from __future__ import annotations

import shutil
from pathlib import Path

from app.cli_support.argument_values import optional_text
from app.cli_support.contracts.codex_command_contracts import CodexMcpInstallCommand
from app.cli_support.contracts.runtime_contracts import CommandContext
from app.cli_support.support.codex.schemas import (
    CodexMcpInstallationResult,
    CodexMcpServerEnvironment,
    CodexMcpServerLaunch,
)
from app.cli_support.url_paths import normalized_base_url
from app.mcp_server.mcp_protocol_enums import (
    McpExecutable,
    McpLaunchArgument,
    McpServerKey,
)
from app.shared.exceptions.cli_exceptions import CliInputError
from app.shared.serialization.model_codec import schema_payload
from app.shared.serialization.orjson_codec import dumps_json
from app.shared.types.extra_types import JSONObject

CODEX_CONFIG_RELATIVE_PATH = "config.toml"
MANAGED_BLOCK_START = "# BEGIN Alexandria-Hermes Codex MCP"
MANAGED_BLOCK_END = "# END Alexandria-Hermes Codex MCP"


def install_codex_mcp_config(
    command: CodexMcpInstallCommand,
    context: CommandContext,
) -> JSONObject:
    """Install or preview Codex MCP configuration.

    Args:
        command: CLI command contract with Codex config options.
        context: Runtime context containing backend defaults and output streams.

    Returns:
        JSON-compatible CLI result with planned and written config state.
    """
    codex_home = resolve_codex_home(command.codex_home)
    api_url = codex_api_url(command, context)
    operator_api_key = command.operator_api_key or ""
    raw_server = build_codex_mcp_server(
        api_url=api_url,
        operator_api_key=operator_api_key,
    )
    written, skipped, backups = apply_codex_mcp_config(
        codex_home=codex_home,
        server=raw_server,
        dry_run=command.dry_run,
        overwrite=command.overwrite,
    )
    result = CodexMcpInstallationResult(
        codex_home=str(codex_home),
        config_path=str(codex_config_path(codex_home)),
        dry_run=command.dry_run,
        written=tuple(written),
        skipped=tuple(skipped),
        backups=tuple(backups),
        mcp_server=build_codex_mcp_server(
            api_url=api_url,
            operator_api_key=redacted_operator_key(operator_api_key),
        ),
        restart_hint=codex_restart_hint(),
    )
    payload = schema_payload(result, by_alias=True)
    return payload


def resolve_codex_home(raw_home: str | None) -> Path:
    """Resolve Codex home from CLI argument or the default location.

    Args:
        raw_home: Optional path supplied by CLI argument.

    Returns:
        Codex home directory path.
    """
    explicit = optional_text(raw_home)
    if explicit is not None:
        return Path(explicit).expanduser()
    return Path.home() / ".codex"


def codex_api_url(
    command: CodexMcpInstallCommand,
    context: CommandContext,
) -> str:
    """Resolve the backend API URL used by Codex MCP integration.

    Args:
        command: CLI command contract with optional API URL.
        context: Runtime context containing the default backend URL.

    Returns:
        Normalized backend API URL.
    """
    raw_url = optional_text(command.api_url)
    if raw_url is not None:
        return normalized_base_url(raw_url)
    return context.base_url


def build_codex_mcp_server(
    api_url: str,
    operator_api_key: str,
) -> CodexMcpServerLaunch:
    """Build the typed Codex MCP server launch contract.

    Args:
        api_url: Backend API URL exposed to the MCP server process.
        operator_api_key: Operator key exposed to the MCP server process.

    Returns:
        Codex MCP server launch configuration.
    """
    return CodexMcpServerLaunch(
        name=McpServerKey.ALEXANDRIA,
        command=McpExecutable.ALEXANDRIA_HERMES,
        args=(McpLaunchArgument.MCP, McpLaunchArgument.SERVE),
        env=CodexMcpServerEnvironment(
            alexandria_api_url=api_url,
            alexandria_operator_api_key=operator_api_key,
        ),
    )


def apply_codex_mcp_config(
    codex_home: Path,
    server: CodexMcpServerLaunch,
    dry_run: bool,
    overwrite: bool,
) -> tuple[list[str], list[str], list[str]]:
    """Write or preview the managed Codex MCP config block.

    Args:
        codex_home: Codex home directory.
        server: MCP server launch configuration to render.
        dry_run: Whether writes should be previewed without filesystem changes.
        overwrite: Whether an existing unmanaged Alexandria server can be replaced.

    Returns:
        Tuple of written, skipped, and backup relative paths.
    """
    config_path = codex_config_path(codex_home)
    current = _read_existing_config(config_path)
    has_managed_block = MANAGED_BLOCK_START in current
    has_unmanaged_server = not has_managed_block and _contains_alexandria_mcp_table(
        current
    )
    if has_unmanaged_server and not overwrite:
        return [], [CODEX_CONFIG_RELATIVE_PATH], []
    rendered = _render_config_content(
        current=current,
        server=server,
        overwrite=overwrite,
    )
    if dry_run:
        return [CODEX_CONFIG_RELATIVE_PATH], [], []
    _validate_codex_config_target(codex_home=codex_home, config_path=config_path)
    backups: list[str] = []
    if config_path.exists():
        backup = config_path.with_name(f"{config_path.name}.bak")
        shutil.copyfile(config_path, backup)
        backups.append(backup.name)
    config_path.write_text(rendered, encoding="utf-8")
    return [CODEX_CONFIG_RELATIVE_PATH], [], backups


def codex_config_path(codex_home: Path) -> Path:
    """Return the Codex config.toml path.

    Args:
        codex_home: Codex home directory.

    Returns:
        Codex config file path.
    """
    return codex_home / CODEX_CONFIG_RELATIVE_PATH


def redacted_operator_key(operator_api_key: str) -> str:
    """Return a safe operator-key value for command output.

    Args:
        operator_api_key: Raw operator key from flags or environment.

    Returns:
        Redacted placeholder for non-empty keys; empty string otherwise.
    """
    return "<REDACTED>" if operator_api_key != "" else ""


def codex_restart_hint() -> str:
    """Return the restart hint shown after Codex MCP installation.

    Returns:
        Restart guidance for Codex sessions.
    """
    return "Restart the active Codex session so the alexandria MCP server is loaded."


def _read_existing_config(config_path: Path) -> str:
    if not config_path.exists():
        return ""
    if not config_path.is_file():
        raise CliInputError(f"Codex config path is not a file: {config_path}")
    return config_path.read_text(encoding="utf-8")


def _validate_codex_config_target(codex_home: Path, config_path: Path) -> None:
    if codex_home.exists() and not codex_home.is_dir():
        raise CliInputError(f"Codex home is not a directory: {codex_home}")
    codex_home.mkdir(parents=True, exist_ok=True)
    if config_path.exists() and not config_path.is_file():
        raise CliInputError(f"Codex config path is not a file: {config_path}")


def _render_config_content(
    current: str,
    server: CodexMcpServerLaunch,
    overwrite: bool,
) -> str:
    block = _managed_mcp_block(server)
    if MANAGED_BLOCK_START in current and MANAGED_BLOCK_END in current:
        before, _start_marker, tail = current.partition(MANAGED_BLOCK_START)
        _managed, marker, after = tail.partition(MANAGED_BLOCK_END)
        if marker == "":
            return _append_block(current, block)
        return _join_config_parts(before.rstrip(), block, after.lstrip())
    content = _remove_alexandria_mcp_tables(current) if overwrite else current
    return _append_block(content, block)


def _append_block(current: str, block: str) -> str:
    if current.strip() == "":
        return f"{block}\n"
    return f"{current.rstrip()}\n\n{block}\n"


def _join_config_parts(before: str, block: str, after: str) -> str:
    pieces = [piece for piece in (before, block, after.rstrip()) if piece != ""]
    return "\n\n".join(pieces) + "\n"


def _managed_mcp_block(server: CodexMcpServerLaunch) -> str:
    env = server.env
    server_name = str(server.name)
    command = str(server.command)
    args = [str(arg) for arg in server.args]
    lines = [
        MANAGED_BLOCK_START,
        "# Managed by alexandria-hermes codex install-mcp.",
        f"[mcp_servers.{server_name}]",
        f"command = {_toml_string(command)}",
        f"args = {_toml_string_array(args)}",
        "",
        f"[mcp_servers.{server_name}.env]",
        f"ALEXANDRIA_API_URL = {_toml_string(env.alexandria_api_url)}",
        "ALEXANDRIA_OPERATOR_API_KEY = "
        f"{_toml_string(env.alexandria_operator_api_key)}",
        MANAGED_BLOCK_END,
    ]
    return "\n".join(lines)


def _toml_string(value: str) -> str:
    return dumps_json(value).decode("utf-8")


def _toml_string_array(values: list[str]) -> str:
    rendered = ", ".join(_toml_string(value) for value in values)
    return f"[{rendered}]"


def _contains_alexandria_mcp_table(content: str) -> bool:
    return any(_is_alexandria_mcp_header(line) for line in content.splitlines())


def _remove_alexandria_mcp_tables(content: str) -> str:
    kept_lines: list[str] = []
    skip = False
    for line in content.splitlines():
        if _is_table_header(line):
            skip = _is_alexandria_mcp_header(line)
        if not skip:
            kept_lines.append(line)
    if len(kept_lines) == 0:
        return ""
    return "\n".join(kept_lines).rstrip() + "\n"


def _is_table_header(line: str) -> bool:
    stripped = line.strip()
    return stripped.startswith("[") and stripped.endswith("]")


def _is_alexandria_mcp_header(line: str) -> bool:
    stripped = line.strip()
    return stripped in {
        "[mcp_servers.alexandria]",
        "[mcp_servers.alexandria.env]",
    } or stripped.startswith("[mcp_servers.alexandria.")
