"""OAuth provider client boundary for librarian provider lifecycle flows."""

from __future__ import annotations

from abc import ABC, abstractmethod

from app.connections.domain.contracts.librarian_oauth_contracts import (
    OAuthDeviceAuthorization,
    OAuthPollResult,
    OAuthTokenSet,
)
from app.connections.domain.entities.read_models import LibrarianProvider


class OAuthProviderClient(ABC):
    """External OAuth provider boundary used by application services."""

    @abstractmethod
    async def start_device_authorization(
        self,
        provider: LibrarianProvider,
    ) -> OAuthDeviceAuthorization:
        """Start OAuth device authorization with a provider.

        Args:
            provider: Provider configuration read model.

        Returns:
            OAuthDeviceAuthorization: User-facing authorization instructions and
            secret device code.
        """

    @abstractmethod
    async def poll_device_token(
        self,
        provider: LibrarianProvider,
        device_code: str,
    ) -> OAuthPollResult:
        """Poll the OAuth token endpoint for a device flow.

        Args:
            provider: Provider configuration read model.
            device_code: Secret device code previously issued by the provider.

        Returns:
            OAuthPollResult: Poll status and optional token set.
        """

    @abstractmethod
    async def refresh_token(
        self,
        provider: LibrarianProvider,
        refresh_token: str,
    ) -> OAuthTokenSet:
        """Refresh an OAuth access token.

        Args:
            provider: Provider configuration read model.
            refresh_token: Secret refresh token from encrypted storage.

        Returns:
            OAuthTokenSet: Rotated token material.
        """
