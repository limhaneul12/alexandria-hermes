"""Shared context construction for librarian CLI commands."""

from __future__ import annotations

from app.cli.librarian_gateway import LibrarianGateway
from app.mcp_server.backend_api_client import AlexandriaApiClient, AlexandriaApiSettings


def build_librarian_gateway() -> LibrarianGateway:
    """Build a librarian gateway from environment-backed API settings.

    Returns:
        Librarian gateway bound to the configured Alexandria backend.
    """
    return LibrarianGateway(AlexandriaApiClient(AlexandriaApiSettings.from_env()))
