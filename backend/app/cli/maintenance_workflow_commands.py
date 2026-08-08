"""Typer apps for Memory Steward and Vault maintenance operations."""

from __future__ import annotations

import typer

from app.cli.memory_steward_commands import register_memory_steward_commands
from app.cli.vault_maintenance_commands import register_vault_maintenance_commands

memory_steward_app = typer.Typer(
    help="Operate Memory Steward readiness and compaction workflows.",
    no_args_is_help=True,
    add_completion=False,
)
register_memory_steward_commands(memory_steward_app)

vault_app = typer.Typer(
    help="Operate Alexandria Core vault review and safe-move workflows.",
    no_args_is_help=True,
    add_completion=False,
)
register_vault_maintenance_commands(vault_app)
