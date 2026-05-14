"""Librarian provider and generation service."""

from __future__ import annotations

from app.library.application.librarians.candidate_generator import build_candidate_stub
from app.library.application.librarians.credential_policy import (
    ensure_create_credentials_are_present,
    ensure_provider_config_has_no_credentials,
)
from app.library.application.librarians.provider_payload_mapper import (
    build_provider_payload,
)
from app.library.domain.contracts.librarian_candidate_contracts import (
    CreateSkillCandidateResult,
)
from app.library.domain.contracts.librarian_provider_contracts import (
    LibrarianProviderCreate,
    LibrarianProviderUpdate,
)
from app.library.domain.event_enum.provider_enums import AuthType, ProviderType
from app.library.domain.repositories.librarian_repository import (
    ILibrarianProviderRepository,
    IProviderSecretRepository,
)
from app.library.domain.types.librarian_provider_payload_types import (
    LibrarianProviderPatchPayload,
    LibrarianProviderPayload,
    LibrarianProviderPayloadList,
    LibrarianProviderTestPayload,
    LibrarianProviderUpdateValues,
)
from app.library.infrastructure.librarians.clients import (
    LibrarianClientFactory,
    LibrarianProviderClientFactory,
)
from app.shared.exceptions import NotFoundError, UnsupportedProviderError
from app.shared.types.extra_types import JSONObject
from app.shared.types.types_convert_utils import now_utc


def _provider_update_values(
    payload: LibrarianProviderPatchPayload,
) -> LibrarianProviderUpdateValues:
    """Build provider patch values without secret fields.

    Args:
        payload: Service-layer patch payload.

    Returns:
        LibrarianProviderUpdateValues: Provider fields safe for repository update.
    """
    values: LibrarianProviderUpdateValues = {}
    if "name" in payload:
        values["name"] = payload["name"]
    if "provider_type" in payload:
        values["provider_type"] = payload["provider_type"]
    if "auth_type" in payload:
        values["auth_type"] = payload["auth_type"]
    if "enabled" in payload:
        values["enabled"] = payload["enabled"]
    if "config" in payload:
        values["config"] = payload["config"]
    return values


class LibrarianService:
    """Service to orchestrate librarian provider settings and usage."""

    def __init__(
        self,
        provider_repo: ILibrarianProviderRepository,
        secret_repo: IProviderSecretRepository,
        client_factory: LibrarianProviderClientFactory | None = None,
    ) -> None:
        """Initialize librarian service dependencies."""
        self.provider_repo = provider_repo
        self.secret_repo = secret_repo
        self.client_factory = (
            LibrarianClientFactory() if client_factory is None else client_factory
        )

    async def create_provider(
        self,
        name: str,
        provider_type: ProviderType,
        auth_type: AuthType,
        enabled: bool,
        config: JSONObject,
        api_key: str | None,
        oauth_access_token: str | None,
    ) -> LibrarianProviderPayload:
        """Create provider and store secrets by provider/auth type.

        Args:
            name: Friendly name.
            provider_type: Provider implementation family.
            auth_type: Authentication mode.
            enabled: Provider enabled flag.
            config: Provider config payload.
            api_key: Optional API key.
            oauth_access_token: Optional OAuth token.

        Returns:
            Provider payload map.
        """
        ensure_provider_config_has_no_credentials(config)
        ensure_create_credentials_are_present(
            auth_type=auth_type,
            api_key=api_key,
            oauth_access_token=oauth_access_token,
        )

        now = now_utc()
        model = await self.provider_repo.create(
            payload=LibrarianProviderCreate(
                name=name,
                provider_type=provider_type,
                auth_type=auth_type,
                enabled=enabled,
                config=config,
                created_at=now,
                updated_at=now,
            ),
        )

        if auth_type is AuthType.API_KEY and api_key:
            await self.secret_repo.set_secret(
                provider_id=model.id,
                key_name="api_key",
                value=api_key,
            )
        if auth_type is AuthType.OAUTH and oauth_access_token:
            await self.secret_repo.set_secret(
                provider_id=model.id,
                key_name="oauth_access_token",
                value=oauth_access_token,
            )

        return build_provider_payload(model)

    async def list_providers(self) -> LibrarianProviderPayloadList:
        """List all providers for response payloads.

        Args:
            None.

        Returns:
            LibrarianProviderPayloadList: Provider payloads without secrets.
        """
        providers = await self.provider_repo.list_all()
        return [build_provider_payload(row) for row in providers]

    async def get_provider(self, provider_id: str) -> LibrarianProviderPayload:
        """Load one provider.

        Args:
            provider_id: Provider id.

        Returns:
            Provider payload dictionary.
        """
        row = await self.provider_repo.get(provider_id)
        if row is None:
            raise NotFoundError(f"Provider not found: {provider_id}")
        return build_provider_payload(row)

    async def update_provider(
        self,
        provider_id: str,
        payload: LibrarianProviderPatchPayload,
    ) -> LibrarianProviderPayload:
        """Patch provider configuration and optional credentials.

        Args:
            provider_id: Provider id.
            payload: Updatable payload with optional secret fields.

        Returns:
            LibrarianProviderPayload: Updated provider payload without secrets.
        """
        row = await self.provider_repo.get(provider_id)
        if row is None:
            raise NotFoundError(f"Provider not found: {provider_id}")

        if "config" in payload:
            ensure_provider_config_has_no_credentials(payload["config"])

        api_key = payload.get("api_key")
        oauth_access_token = payload.get("oauth_access_token")
        auth_type = (
            payload["auth_type"] if "auth_type" in payload else AuthType(row.auth_type)
        )

        if auth_type is AuthType.API_KEY and api_key is None:
            existing_api_key = await self.secret_repo.resolve(provider_id, "api_key")
            if not existing_api_key:
                raise UnsupportedProviderError("API_KEY auth requires api_key")
        if auth_type is AuthType.OAUTH and oauth_access_token is None:
            existing_oauth_token = await self.secret_repo.resolve(
                provider_id, "oauth_access_token"
            )
            if not existing_oauth_token:
                raise UnsupportedProviderError("OAUTH auth requires oauth_access_token")

        updated = await self.provider_repo.update(
            provider_id,
            payload=LibrarianProviderUpdate(values=_provider_update_values(payload)),
        )

        if auth_type is AuthType.API_KEY and api_key is not None:
            await self.secret_repo.set_secret(
                provider_id=provider_id,
                key_name="api_key",
                value=api_key,
            )
        if auth_type is AuthType.OAUTH and oauth_access_token is not None:
            await self.secret_repo.set_secret(
                provider_id=provider_id,
                key_name="oauth_access_token",
                value=oauth_access_token,
            )

        return build_provider_payload(updated)

    async def delete_provider(self, provider_id: str) -> None:
        """Delete provider and all secrets.

        Args:
            provider_id: Provider id.

        Returns:
            None.
        """
        row = await self.provider_repo.get(provider_id)
        if row is None:
            raise NotFoundError(f"Provider not found: {provider_id}")
        await self.provider_repo.delete(provider_id)

    async def test_provider(
        self,
        provider_id: str,
        test_query: str,
    ) -> LibrarianProviderTestPayload:
        """Verify provider registration and required credential path.

        Args:
            provider_id: Provider id.
            test_query: Text submitted for a dry run.

        Returns:
            Test result map.
        """
        model = await self.provider_repo.get(provider_id)
        if model is None:
            raise NotFoundError(f"Provider not found: {provider_id}")
        result = await self.client_factory.test_connection(
            provider=model,
            secret_resolver=self.secret_repo,
            test_query=test_query,
        )
        return result.as_public_dict()

    def generate_candidate_stub(
        self,
        provider_id: str,
        prompt: str,
        seed: int | None = None,
    ) -> CreateSkillCandidateResult:
        """Generate deterministic candidate payload for prompt.

        Args:
            provider_id: Provider id used by caller.
            prompt: Natural-language request.
            seed: Optional deterministic seed.

        Returns:
        Typed candidate result.
        """
        candidate_result = build_candidate_stub(
            provider_id=provider_id,
            prompt=prompt,
            seed=seed,
        )
        return candidate_result
