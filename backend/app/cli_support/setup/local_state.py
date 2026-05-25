"""Runtime setup local-state path resolution."""

from __future__ import annotations

from dataclasses import dataclass
from os import environ as process_environment
from pathlib import Path


@dataclass(frozen=True, slots=True)
class AlexandriaLocalState:
    """Resolved local runtime state paths for Alexandria-Hermes."""

    hermes_home: Path
    root: Path
    env_path: Path
    data_dir: Path
    database_path: Path
    database_url: str
    obsidian_vault_path: Path
    logs_dir: Path
    backend_log_path: Path
    run_dir: Path
    guidebook_path: Path


def resolve_local_state(hermes_home: str | None) -> AlexandriaLocalState:
    """Resolve Hermes-style local state paths.

    Args:
        hermes_home: Explicit Hermes home override, when provided.

    Returns:
        Fully resolved Alexandria local-state path bundle.
    """
    home_source = hermes_home or process_environment.get("HERMES_HOME") or "~/.hermes"
    resolved_home = Path(home_source).expanduser().resolve()
    root = resolved_home / "alexandria-hermes"
    data_dir = root / "data"
    database_path = data_dir / "alexandria_hermes.db"
    obsidian_vault_path = data_dir / "obsidian-vault"
    logs_dir = root / "logs"
    run_dir = root / "run"
    return AlexandriaLocalState(
        hermes_home=resolved_home,
        root=root,
        env_path=root / ".env",
        data_dir=data_dir,
        database_path=database_path,
        database_url=f"sqlite+aiosqlite:///{database_path}",
        obsidian_vault_path=obsidian_vault_path,
        logs_dir=logs_dir,
        backend_log_path=logs_dir / "backend.log",
        run_dir=run_dir,
        guidebook_path=root / "GUIDEBOOK.md",
    )
