"""Shared exceptions raised by CLI adapters."""

from __future__ import annotations


class CliRequestError(Exception):
    """HTTP request failure surfaced as a CLI error."""

    def __init__(self, status_code: int, message: str) -> None:
        """Initialize the CLI request error.

        Args:
            status_code: HTTP status code or zero for transport failures.
            message: Human-readable error message.

        Returns:
            None.
        """
        self.status_code = status_code
        self.message = message
        super().__init__(f"HTTP {status_code}: {message}")


class CliInputError(Exception):
    """Invalid CLI input with stable user-facing meaning."""


class CliRuntimeStateError(Exception):
    """Invalid CLI runtime wiring detected before command execution."""
