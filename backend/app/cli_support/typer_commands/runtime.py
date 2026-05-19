"""Typer command for foreground backend runtime."""

from __future__ import annotations

import typer
from app.cli_support.contracts.command_contracts import ServeCommand
from app.cli_support.handlers.runtime import handle_serve


def serve_command(
    env_file: str | None = typer.Option(
        None,
        "--env-file",
        help="Load generated backend + SQLite local daemon environment file.",
    ),
    host: str = typer.Option(
        "127.0.0.1",
        "--host",
        help="Backend bind host for the local SQLite companion service.",
    ),
    port: int = typer.Option(
        8000,
        "--port",
        help="Backend bind port for the local SQLite companion service.",
    ),
    reload: bool = typer.Option(
        False,
        "--reload",
        help="Enable uvicorn reload for local development.",
    ),
) -> None:
    """Run the Alexandria-Hermes backend with the SQLite local DB in foreground.

    Args:
        env_file: Optional environment file to load before starting.
        host: Backend bind host.
        port: Backend bind port.
        reload: Whether to enable uvicorn reload for local development.
    """
    raise typer.Exit(
        handle_serve(
            ServeCommand(
                env_file=env_file,
                host=host,
                port=port,
                reload=reload,
            )
        )
    )
