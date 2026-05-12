"""Librarian provider repository abstraction."""

from __future__ import annotations

from abc import ABC, abstractmethod

from app.library.domain.entities.read_models import LibrarianProvider
from app.shared.types.extra_types import JSONValue


class LibrarianProviderRepository(ABC):
    """Persistence contract for librarian provider settings."""

    @abstractmethod
    async def create(self, payload: dict[str, JSONValue]) -> LibrarianProvider:
        """Create a provider entry."""

    @abstractmethod
    async def get(self, provider_id: int) -> LibrarianProvider | None:
        """Get one provider."""

    @abstractmethod
    async def list_all(self) -> list[LibrarianProvider]:
        """List all providers."""

    @abstractmethod
    async def update(
        self, provider_id: int, payload: dict[str, JSONValue]
    ) -> LibrarianProvider:
        """Patch provider settings."""

    @abstractmethod
    async def delete(self, provider_id: int) -> None:
        """Delete one provider."""


class ProviderSecretRepository(ABC):
    """Persistence contract for librarian provider secrets."""

    @abstractmethod
    async def resolve(self, provider_id: int, key_name: str) -> str | None:
        """Return secret value by key name."""

    @abstractmethod
    async def set_secret(self, *, provider_id: int, key_name: str, value: str) -> None:
        """Persist or update one provider secret."""

    @abstractmethod
    async def delete_for_provider(self, provider_id: int, key_name: str) -> None:
        """Delete one provider secret key."""
