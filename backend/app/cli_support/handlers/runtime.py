"""Runtime command handlers."""

from __future__ import annotations

from os import environ as process_environment
from pathlib import Path

import uvicorn
from app.cli_support.contracts.runtime_command_contracts import ServeCommand


def handle_serve(command: ServeCommand) -> int:
    """Run the FastAPI backend in the foreground.

    Args:
        command: Serve command options.

    Returns:
        Process exit code when the server exits normally.
    """
    if command.env_file is not None:
        _load_env_file(Path(command.env_file).expanduser())

    uvicorn.run(
        "app.main:app",
        host=command.host,
        port=command.port,
        reload=command.reload,
    )
    return 0


def _load_env_file(path: Path) -> None:
    if not path.exists():
        raise FileNotFoundError(path)
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)

        process_environment.setdefault(key, value)
