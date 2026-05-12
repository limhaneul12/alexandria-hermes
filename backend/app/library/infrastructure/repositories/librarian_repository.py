"""Librarian provider repository implementation."""

from __future__ import annotations

from datetime import UTC, datetime

from app.library.domain.entities.read_models import LibrarianProvider
from app.library.domain.repositories.librarian_repository import (
    LibrarianProviderRepository,
    ProviderSecretRepository as ProviderSecretRepositoryPort,
)
from app.library.infrastructure.models.librarian_provider import (
    LibrarianProviderORM,
    ProviderSecretORM,
)
from app.shared.exceptions import NotFoundError
from app.shared.types.extra_types import JSONValue
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession


def _to_read_model(row: LibrarianProviderORM) -> LibrarianProvider:
    """Map a librarian provider ORM row into the domain read model."""
    return LibrarianProvider(
        id=row.id,
        name=row.name,
        provider_type=row.provider_type,
        auth_type=row.auth_type,
        enabled=row.enabled,
        config=row.config,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


class SqlAlchemyLibrarianProviderRepository(LibrarianProviderRepository):
    """Persistence for librarian provider configuration."""

    def __init__(self, *, session: AsyncSession) -> None:
        """Initialize repository.

        Args:
            session: Active async session.
        """
        self._session = session

    async def create(self, payload: dict[str, JSONValue]) -> LibrarianProvider:
        """Create provider and optional secret records."""
        secret_fields = payload.pop("secrets", None)
        model = LibrarianProviderORM(**payload)
        self._session.add(model)
        await self._session.flush()
        if isinstance(secret_fields, dict):
            for key, value in secret_fields.items():
                self._session.add(
                    ProviderSecretORM(
                        provider_id=model.id,
                        key_name=key,
                        value=str(value),
                    )
                )
        await self._session.flush()
        return _to_read_model(model)

    async def get(self, provider_id: int) -> LibrarianProvider | None:
        """Get one provider by id."""
        model = await self._session.get(LibrarianProviderORM, provider_id)
        return None if model is None else _to_read_model(model)

    async def list_all(self) -> list[LibrarianProvider]:
        """List all provider records."""
        rows = await self._session.execute(select(LibrarianProviderORM))
        return [_to_read_model(row) for row in rows.scalars().all()]

    async def update(
        self,
        provider_id: int,
        payload: dict[str, JSONValue],
    ) -> LibrarianProvider:
        """Patch provider fields and secret values."""
        model = await self._session.get(LibrarianProviderORM, provider_id)
        if model is None:
            raise NotFoundError(f"Provider not found: {provider_id}")

        secret_fields = payload.pop("secrets", None)
        for key, value in payload.items():
            setattr(model, key, value)
        model.updated_at = datetime.now(UTC)

        if isinstance(secret_fields, dict):
            await self._session.execute(
                delete(ProviderSecretORM).where(
                    ProviderSecretORM.provider_id == provider_id,
                )
            )
            for key, value in secret_fields.items():
                self._session.add(
                    ProviderSecretORM(
                        provider_id=provider_id,
                        key_name=key,
                        value=str(value),
                    )
                )

        await self._session.flush()
        return _to_read_model(model)

    async def delete(self, provider_id: int) -> None:
        """Delete provider and dependent secrets."""
        model = await self._session.get(LibrarianProviderORM, provider_id)
        if model is None:
            raise NotFoundError(f"Provider not found: {provider_id}")

        await self._session.execute(
            delete(LibrarianProviderORM).where(LibrarianProviderORM.id == provider_id)
        )
        await self._session.flush()


class ProviderSecretRepository(ProviderSecretRepositoryPort):
    """Separate access to secret records for test and redaction safety."""

    def __init__(self, *, session: AsyncSession) -> None:
        """Initialize secret repository.

        Args:
            session: Active async session.
        """
        self._session = session

    async def resolve(self, provider_id: int, key_name: str) -> str | None:
        """Return secret value by key name."""
        query = select(ProviderSecretORM.value).where(
            ProviderSecretORM.provider_id == provider_id,
            ProviderSecretORM.key_name == key_name,
        )
        value = await self._session.scalar(query)
        return value

    async def set_secret(self, *, provider_id: int, key_name: str, value: str) -> None:
        """Upsert one provider secret by key."""
        existing = await self._session.scalar(
            select(ProviderSecretORM).where(
                ProviderSecretORM.provider_id == provider_id,
                ProviderSecretORM.key_name == key_name,
            )
        )
        if isinstance(existing, ProviderSecretORM):
            existing.value = value
        else:
            self._session.add(
                ProviderSecretORM(
                    provider_id=provider_id,
                    key_name=key_name,
                    value=value,
                )
            )
        await self._session.flush()

    async def delete_for_provider(self, provider_id: int, key_name: str) -> None:
        """Delete one secret key from a provider."""
        await self._session.execute(
            delete(ProviderSecretORM).where(
                ProviderSecretORM.provider_id == provider_id,
                ProviderSecretORM.key_name == key_name,
            )
        )
        await self._session.flush()
