"""Compatibility imports for librarian provider client contracts."""

from __future__ import annotations

from app.connections.domain.contracts.librarian_client_contracts import (
    ApiKeyCredential,
    LibrarianProviderClientFactory,
    ProviderClientTestResult,
)
from app.connections.domain.repositories.librarian_repository import (
    IProviderSecretRepository as SecretResolver,
)

__all__ = [
    "ApiKeyCredential",
    "LibrarianProviderClientFactory",
    "ProviderClientTestResult",
    "SecretResolver",
]
