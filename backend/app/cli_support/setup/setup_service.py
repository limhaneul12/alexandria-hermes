"""Runtime setup planning and file-write side effects."""

from __future__ import annotations

import secrets
from pathlib import Path

from app.cli_support.contracts.runtime_command_contracts import (
    SetupCommand,
    SetupRuntimeMode,
)
from app.cli_support.setup.local_state import AlexandriaLocalState, resolve_local_state
from app.cli_support.setup.migrations import run_alembic_upgrade
from app.cli_support.setup.setup_schemas import (
    HermesAssetsSetupSummary,
    MigrationSetupSummary,
    SetupSummary,
)
from app.cli_support.support.hermes.install.asset_sources import (
    load_alexandria_prompt_sources,
    load_alexandria_skill_source,
)
from app.cli_support.support.hermes.install.policy_files import default_policy_yaml
from app.shared.exceptions.cli_exceptions import CliInputError

ASSET_SKILL_TARGET = "skills/alexandria-hermes/alexandria-library/SKILL.md"
ASSET_POLICY_TARGET = "alexandria-hermes/policy.yaml"
PROMPT_TARGET_PREFIX = "prompts/alexandria-hermes"
DEFAULT_ALEXANDRIA_OBSIDIAN_ROOT = "Alexandria"


def handle_setup(command: SetupCommand) -> SetupSummary:
    """Plan and optionally apply the Alexandria-Hermes runtime setup.

    Args:
        command: User-selected runtime setup options.

    Returns:
        Typed setup summary for CLI presentation.
    """
    if command.mode is None and command.non_interactive:
        raise CliInputError(
            "--mode is required for --non-interactive setup; ask the user which "
            "runtime mode they want first."
        )
    selected_mode = command.mode or SetupRuntimeMode.BACKEND_DAEMON
    state = resolve_local_state(command.hermes_home)
    obsidian_vault_path = _resolved_obsidian_vault_path(command, state)
    alexandria_obsidian_root = _alexandria_obsidian_root(command)
    memory_compact_note_dir = _memory_compact_note_dir(alexandria_obsidian_root)
    planned_assets = _planned_hermes_asset_files(command.install_hermes_assets)
    should_apply = command.apply and not command.dry_run
    env_written = False
    guidebook_written = False
    written_assets: list[str] = []
    migration_status = "not_requested"
    migration_revision: str | None = None
    if should_apply:
        state.root.mkdir(parents=True, exist_ok=True)
        for directory in (
            state.data_dir,
            obsidian_vault_path,
            state.logs_dir,
            state.run_dir,
        ):
            directory.mkdir(parents=True, exist_ok=True)
        _write_env(
            command,
            selected_mode,
            state,
            obsidian_vault_path,
            alexandria_obsidian_root,
            memory_compact_note_dir,
        )
        env_written = True
        if command.write_guidebook:
            state.guidebook_path.write_text(
                _guidebook_text(
                    selected_mode,
                    state,
                    obsidian_vault_path,
                    alexandria_obsidian_root,
                    memory_compact_note_dir,
                ),
                encoding="utf-8",
            )
            guidebook_written = True
        if command.install_hermes_assets:
            written_assets = _write_hermes_assets(state.hermes_home)
        if command.run_migrations:
            migration = run_alembic_upgrade(database_url=state.database_url)
            migration_status = migration.status
            migration_revision = migration.revision
    return SetupSummary(
        mode=selected_mode.value,
        dry_run=command.dry_run,
        applied=should_apply,
        hermes_home=str(state.hermes_home),
        state_root=str(state.root),
        env_path=str(_resolved_env_path(command, state)),
        env_written=env_written,
        database_path=str(state.database_path),
        database_url=state.database_url,
        obsidian_vault_path=str(obsidian_vault_path),
        alexandria_obsidian_root=alexandria_obsidian_root,
        backend_log_path=str(state.backend_log_path),
        run_dir=str(state.run_dir),
        guidebook_path=str(state.guidebook_path),
        guidebook_written=guidebook_written,
        hermes_assets_planned=command.install_hermes_assets,
        hermes_assets=HermesAssetsSetupSummary(
            planned_files=planned_assets,
            written_files=written_assets,
        ),
        migrations=MigrationSetupSummary(
            run_requested=command.run_migrations,
            status=migration_status,
            revision=migration_revision,
        ),
        next_steps=_next_steps(
            selected_mode, state, run_migrations=command.run_migrations
        ),
    )


def _write_env(
    command: SetupCommand,
    selected_mode: SetupRuntimeMode,
    state: AlexandriaLocalState,
    obsidian_vault_path: Path,
    alexandria_obsidian_root: str,
    memory_compact_note_dir: str,
) -> None:
    env_path = _resolved_env_path(command, state)
    env_path.parent.mkdir(parents=True, exist_ok=True)
    env_path.write_text(
        _env_text(
            command,
            selected_mode,
            state,
            obsidian_vault_path,
            alexandria_obsidian_root,
            memory_compact_note_dir,
        ),
        encoding="utf-8",
    )


def _resolved_env_path(command: SetupCommand, state: AlexandriaLocalState) -> Path:
    if command.env_path is None:
        return state.env_path
    return Path(command.env_path).expanduser().resolve()


def _resolved_obsidian_vault_path(
    command: SetupCommand, state: AlexandriaLocalState
) -> Path:
    if command.obsidian_vault_path is None:
        return state.obsidian_vault_path
    return Path(command.obsidian_vault_path).expanduser().resolve()


def _alexandria_obsidian_root(command: SetupCommand) -> str:
    if command.alexandria_obsidian_root is None:
        return DEFAULT_ALEXANDRIA_OBSIDIAN_ROOT
    return command.alexandria_obsidian_root


def _memory_compact_note_dir(alexandria_obsidian_root: str) -> str:
    if alexandria_obsidian_root in {"", "."}:
        return "Memory Compacts"
    return f"{alexandria_obsidian_root}/Memory Compacts"


def _env_text(
    command: SetupCommand,
    selected_mode: SetupRuntimeMode,
    state: AlexandriaLocalState,
    obsidian_vault_path: Path,
    alexandria_obsidian_root: str,
    memory_compact_note_dir: str,
) -> str:
    api_url = command.api_url or "http://127.0.0.1:8000"
    operator_api_key = command.operator_api_key or secrets.token_urlsafe(32)
    return "\n".join(
        [
            "# Generated by alexandria-hermes setup.",
            f"ALEXANDRIA_RUNTIME_MODE={selected_mode.value}",
            "ALEXANDRIA_DB_BACKEND=sqlite",
            f"DATABASE_URL={state.database_url}",
            f"ALEXANDRIA_OPERATOR_API_KEY={operator_api_key}",
            f"HERMES_API_URL={api_url}",
            f"ALEXANDRIA_STATE_HOME={state.root}",
            f"SERVICE_OBSIDIAN_VAULT_PATH={obsidian_vault_path}",
            f"SERVICE_ALEXANDRIA_OBSIDIAN_ROOT={alexandria_obsidian_root}",
            f"SERVICE_MEMORY_COMPACT_NOTE_DIR={memory_compact_note_dir}",
            f"ALEXANDRIA_BACKEND_LOG={state.backend_log_path}",
            "",
        ]
    )


def _planned_hermes_asset_files(enabled: bool) -> list[str]:
    if not enabled:
        return []
    prompt_files = [
        f"{PROMPT_TARGET_PREFIX}/{name}" for name in load_alexandria_prompt_sources()
    ]
    return [ASSET_SKILL_TARGET, *prompt_files, ASSET_POLICY_TARGET]


def _write_hermes_assets(hermes_home: Path) -> list[str]:
    written: list[str] = []
    _write_relative(hermes_home, ASSET_SKILL_TARGET, load_alexandria_skill_source())
    written.append(ASSET_SKILL_TARGET)
    for prompt_name, prompt_text in load_alexandria_prompt_sources().items():
        target = f"{PROMPT_TARGET_PREFIX}/{prompt_name}"
        _write_relative(hermes_home, target, prompt_text)
        written.append(target)
    _write_relative(hermes_home, ASSET_POLICY_TARGET, default_policy_yaml())
    written.append(ASSET_POLICY_TARGET)
    return written


def _write_relative(base: Path, relative_path: str, content: str) -> None:
    target = base / relative_path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")


def _next_steps(
    mode: SetupRuntimeMode,
    state: AlexandriaLocalState,
    *,
    run_migrations: bool = False,
) -> list[str]:
    shared = [
        "Run alexandria-hermes hermes policy status to confirm Alexandria is enabled or disabled as desired.",
        "Run alexandria-hermes hermes onboard when you want Hermes prompt/MCP integration assets installed.",
    ]
    migration_step = (
        []
        if run_migrations
        else [
            "Run setup again with --run-migrations, or run alembic upgrade head before first backend use."
        ]
    )
    per_mode = {
        SetupRuntimeMode.BACKEND_DAEMON: [
            f"Use {state.env_path} for local Backend + SQLite daemon configuration.",
            *migration_step,
            "Start the backend daemon with the generated env file before connecting Hermes.",
        ],
        SetupRuntimeMode.GUIDEBOOK_ONLY: [
            "Read the generated guidebook and choose a runtime mode before applying setup.",
        ],
    }
    return [*per_mode[mode], *shared]


def _guidebook_text(
    mode: SetupRuntimeMode,
    state: AlexandriaLocalState,
    obsidian_vault_path: Path,
    alexandria_obsidian_root: str,
    memory_compact_note_dir: str,
) -> str:
    steps = "\n".join(
        f"- {step}" for step in _next_steps(mode, state, run_migrations=False)
    )
    root_hint = (
        "The vault root itself is managed because `SERVICE_ALEXANDRIA_OBSIDIAN_ROOT=.`."
        if alexandria_obsidian_root == "."
        else f"Alexandria-managed notes live under `{alexandria_obsidian_root}/`."
    )
    return f"""# Alexandria-Hermes Local Guidebook

## Selected runtime

{_mode_title(mode)}

## Local state

- Env: `{state.env_path}`
- SQLite database: `{state.database_path}`
- Obsidian vault: `{obsidian_vault_path}`
- Alexandria root in vault: `{alexandria_obsidian_root}`
- Memory Compact folder: `{memory_compact_note_dir}`
- Backend log: `{state.backend_log_path}`
- Run dir: `{state.run_dir}`

{root_hint}

## Commands

{steps}

## On/off controls

- Disable optional Alexandria usage: `alexandria-hermes hermes policy disable`
- Re-enable optional Alexandria usage: `alexandria-hermes hermes policy enable`
- Check status/diagnostics: `alexandria-hermes hermes policy status` and `alexandria-hermes hermes doctor`

## Hermes awareness

Alexandria installation alone does not make Hermes use it. Run `alexandria-hermes hermes onboard` or install the `skills_alexandria` assets so Hermes has the skill/prompt contract.

## Obsidian

- Install/open Obsidian, then open the generated vault path above.
- Initialize folders with `alexandria-hermes obsidian init` after the backend is running.
- Rebuild search with `alexandria-hermes obsidian reindex`.
"""


def _mode_title(mode: SetupRuntimeMode) -> str:
    titles = {
        SetupRuntimeMode.BACKEND_DAEMON: "Backend + SQLite daemon",
        SetupRuntimeMode.GUIDEBOOK_ONLY: "Guidebook-only planning",
    }
    return titles[mode]
