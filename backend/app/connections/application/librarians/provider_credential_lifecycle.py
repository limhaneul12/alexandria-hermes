"""Provider credential presence and cleanup boundary."""

from __future__ import annotations

from app.connections.domain.event_enum.provider_enums import ProviderSecretKey
from app.connections.domain.repositories.librarian_repository import (
    IProviderSecretRepository,
)

OAUTH_PROVIDER_CREDENTIAL_KEYS: tuple[ProviderSecretKey, ...] = (
    ProviderSecretKey.OAUTH_ACCESS_TOKEN,
    ProviderSecretKey.OAUTH_REFRESH_TOKEN,
    ProviderSecretKey.OAUTH_EXPIRES_AT,
    ProviderSecretKey.OAUTH_TOKEN_TYPE,
    ProviderSecretKey.OAUTH_SCOPE,
    ProviderSecretKey.OAUTH_DEVICE_CODE,
    ProviderSecretKey.OAUTH_DEVICE_EXPIRES_AT,
    ProviderSecretKey.OAUTH_POLL_INTERVAL_SECONDS,
)
ALL_PROVIDER_CREDENTIAL_KEYS: tuple[ProviderSecretKey, ...] = tuple(ProviderSecretKey)


class ProviderCredentialLifecycle:
    """Inspect and remove encrypted provider credentials by logical key group."""

    def __init__(self, repository: IProviderSecretRepository) -> None:
        """Create the provider credential lifecycle boundary.

        Args:
            repository: Encrypted provider credential repository.
        """
        self._repository = repository

    async def oauth_credentials_exist(self, provider_id: str) -> bool:
        """Return whether any OAuth credential is stored for one provider.

        Args:
            provider_id: Provider identifier.

        Returns:
            Whether at least one OAuth credential exists.
        """
        for key in OAUTH_PROVIDER_CREDENTIAL_KEYS:
            credential = await self._repository.resolve(provider_id, key.value)
            if credential:
                return True
        return False

    async def delete_all(self, provider_id: str) -> None:
        """Delete every known credential for one provider.

        Args:
            provider_id: Provider identifier.
        """
        for key in ALL_PROVIDER_CREDENTIAL_KEYS:
            await self._repository.delete_for_provider(provider_id, key.value)
