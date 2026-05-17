"""Typed CLI environment access boundary."""

from __future__ import annotations

from os import environ as _process_environment


def cli_secret_value(env_name: str) -> str | None:
    """Return one CLI-provided secret environment value.

    Args:
        env_name: Environment variable name supplied by an operator CLI option.

    Returns:
        Non-empty environment value, or None.
    """
    value = _process_environment.get(env_name)
    if value is None:
        return None
    stripped = value.strip()
    return stripped or None
