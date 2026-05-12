"""Librarian provider and generation service."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass

from app.library.application.common import now_utc
from app.library.domain.entities.enums import AuthType, ProviderType
from app.library.domain.entities.read_models import LibrarianProvider
from app.library.domain.repositories.librarian_repository import (
    LibrarianProviderRepository,
    ProviderSecretRepository,
)
from app.shared.exceptions import NotFoundError, UnsupportedProviderError
from app.shared.types.extra_types import JSONValue


@dataclass(frozen=True)
class LibrarianService:
    """Service to orchestrate librarian provider settings and usage."""

    provider_repo: LibrarianProviderRepository
    secret_repo: ProviderSecretRepository

    async def create_provider(
        self,
        *,
        name: str,
        provider_type: ProviderType,
        auth_type: AuthType,
        enabled: bool,
        config: dict[str, JSONValue],
        api_key: str | None,
        oauth_access_token: str | None,
    ) -> dict[str, JSONValue]:
        """Create provider and store secrets by provider/auth type.

        Args:
            name: Friendly name.
            provider_type: Provider implementation family.
            auth_type: Authentication mode.
            enabled: Provider enabled flag.
            config: Provider config payload.
            api_key: Optional API key.
            oauth_access_token: Optional OAuth token.

        Return:
            Provider payload map.
        """
        if auth_type is AuthType.API_KEY and not api_key:
            raise UnsupportedProviderError("API_KEY auth requires api_key")
        if auth_type is AuthType.OAUTH and not oauth_access_token:
            raise UnsupportedProviderError("OAUTH auth requires oauth_access_token")

        now = now_utc()
        model = await self.provider_repo.create(
            payload={
                "name": name,
                "provider_type": provider_type.value,
                "auth_type": auth_type.value,
                "enabled": enabled,
                "config": config,
                "created_at": now,
                "updated_at": now,
            },
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

        return self._model_to_payload(model)

    async def list_providers(self) -> list[dict[str, JSONValue]]:
        """List all providers for response payloads.

        Args:
            None.

        Return:
            List of provider payload dictionaries.
        """
        providers = await self.provider_repo.list_all()
        return [self._model_to_payload(row) for row in providers]

    async def get_provider(self, provider_id: int) -> dict[str, JSONValue]:
        """Load one provider.

        Args:
            provider_id: Provider id.

        Return:
            Provider payload dictionary.
        """
        row = await self.provider_repo.get(provider_id)
        if row is None:
            raise NotFoundError(f"Provider not found: {provider_id}")
        return self._model_to_payload(row)

    async def update_provider(
        self,
        provider_id: int,
        *,
        payload: dict[str, JSONValue],
    ) -> dict[str, JSONValue]:
        """Patch provider configuration and optional credentials.

        Args:
            provider_id: Provider id.
            payload: Updatable payload with optional secret fields.

        Return:
            Updated provider payload.
        """
        row = await self.provider_repo.get(provider_id)
        if row is None:
            raise NotFoundError(f"Provider not found: {provider_id}")

        api_key = payload.pop("api_key", None)
        oauth_access_token = payload.pop("oauth_access_token", None)
        auth_type = payload.get("auth_type", row.auth_type)
        if not isinstance(auth_type, str):
            auth_type = str(auth_type)

        updated = await self.provider_repo.update(
            provider_id,
            payload={key: value for key, value in payload.items() if value is not None},
        )

        if auth_type == AuthType.API_KEY.value and isinstance(api_key, str):
            await self.secret_repo.set_secret(
                provider_id=provider_id,
                key_name="api_key",
                value=api_key,
            )
        if auth_type == AuthType.OAUTH.value and isinstance(oauth_access_token, str):
            await self.secret_repo.set_secret(
                provider_id=provider_id,
                key_name="oauth_access_token",
                value=oauth_access_token,
            )

        return self._model_to_payload(updated)

    async def delete_provider(self, provider_id: int) -> None:
        """Delete provider and all secrets.

        Args:
            provider_id: Provider id.

        Return:
            None.
        """
        row = await self.provider_repo.get(provider_id)
        if row is None:
            raise NotFoundError(f"Provider not found: {provider_id}")
        await self.provider_repo.delete(provider_id)

    async def test_provider(
        self,
        provider_id: int,
        test_query: str,
    ) -> dict[str, JSONValue]:
        """Verify provider registration and required credential path.

        Args:
            provider_id: Provider id.
            test_query: Text submitted for a dry run.

        Return:
            Test result map.
        """
        model = await self.provider_repo.get(provider_id)
        if model is None:
            raise NotFoundError(f"Provider not found: {provider_id}")
        if not model.enabled:
            return {
                "provider_id": provider_id,
                "ok": False,
                "message": "provider disabled",
            }

        if model.auth_type == AuthType.API_KEY.value:
            api_key = await self.secret_repo.resolve(provider_id, "api_key")
            if not api_key:
                return {
                    "provider_id": provider_id,
                    "ok": False,
                    "message": "api_key missing",
                }

        if model.auth_type == AuthType.OAUTH.value:
            oauth_token = await self.secret_repo.resolve(
                provider_id, "oauth_access_token"
            )
            if not oauth_token:
                return {
                    "provider_id": provider_id,
                    "ok": False,
                    "message": "oauth_access_token missing",
                }

        return {
            "provider_id": provider_id,
            "ok": True,
            "message": f"provider test accepted query '{test_query}'",
        }

    def generate_candidate_stub(
        self,
        *,
        provider_id: int,
        prompt: str,
        seed: int | None = None,
    ) -> dict[str, JSONValue]:
        """Generate deterministic candidate payload for prompt.

        Args:
            provider_id: Provider id used by caller.
            prompt: Natural-language request.
            seed: Optional deterministic seed.

        Return:
            Candidate dictionary.
        """
        normalized = prompt.strip().replace("\n", " ")
        seed_text = "" if seed is None else str(seed)
        digest = hashlib.sha256(
            f"{provider_id}:{normalized}:{seed_text}".encode()
        ).hexdigest()[:8]
        title_prefix = normalized[:60] if normalized else "Generated skill"
        title = f"{title_prefix} [{digest}]"
        return {
            "title": title,
            "summary": f"Auto-generated skill candidate ({digest})",
            "content": f"Generated skill from librarian {provider_id}: {normalized}",
            "purpose": normalized,
            "input_schema": {
                "type": "object",
                "properties": {
                    "request": {
                        "type": "string",
                    },
                },
            },
            "output_schema": {
                "type": "object",
                "properties": {
                    "result": {
                        "type": "string",
                    },
                },
            },
            "required_tools": ["planner"],
            "risk_level": "LOW",
            "version": "1.0.0",
            "prompt": normalized,
            "provider_id": provider_id,
        }

    @staticmethod
    def _model_to_payload(model: LibrarianProvider) -> dict[str, JSONValue]:
        """Map provider ORM row into public payload.

        Args:
            model: Provider ORM-like object.

        Return:
            API payload dictionary.
        """
        return {
            "id": model.id,
            "name": model.name,
            "provider_type": model.provider_type,
            "auth_type": model.auth_type,
            "enabled": model.enabled,
            "config": model.config,
            "created_at": model.created_at,
            "updated_at": model.updated_at,
        }
