"""Provider connection scope tests."""

from __future__ import annotations

from datetime import UTC, datetime

import anyio
from app.library.domain.entities.read_models import LibrarianProvider
from app.library.domain.event_enum.provider_enums import AuthType, ProviderType
from app.library.infrastructure.librarians.clients import (
    LibrarianClientFactory,
    ProviderClientTestResult,
)
from app.library.infrastructure.librarians.openai_adapter import OpenAIClientConfig
from app.shared.types.extra_types import JSONValue
from openai import OpenAI

PROVIDER_ID = "00000000-0000-4000-8000-000000000777"
SECRET_VALUE = "sk-test"


class StaticSecretResolver:
    """Provider secret resolver test double."""

    async def resolve(self, provider_id: str, key_name: str) -> str | None:
        """Return a deterministic API key for connection checks."""
        return SECRET_VALUE


class ExplodingOpenAIClientBuilder:
    """OpenAI SDK builder that fails if non-OpenAI providers instantiate it."""

    def __call__(self, config: OpenAIClientConfig) -> OpenAI:
        """Raise if client construction is attempted."""
        raise AssertionError(f"SDK client should not instantiate: {config!r}")


def _provider(
    provider_type: str, config: dict[str, JSONValue] | None = None
) -> LibrarianProvider:
    """Build a provider row with a raw persisted provider type."""
    timestamp = datetime(2026, 5, 13, 11, 30, tzinfo=UTC)
    return LibrarianProvider(
        id=PROVIDER_ID,
        name="sdk-backed librarian",
        provider_type=provider_type,
        auth_type=AuthType.API_KEY.value,
        enabled=True,
        config={} if config is None else config,
        created_at=timestamp,
        updated_at=timestamp,
    )


def test_provider_type_enum_keeps_only_openai_agent_connection_and_minio_storage() -> (
    None
):
    """Non-OpenAI agent provider choices should not remain in the public enum."""
    assert {provider_type.value for provider_type in ProviderType} == {
        "OPENAI",
        "MINIO",
    }


def test_connection_rejects_non_openai_agent_provider_rows_without_sdk_construction() -> (
    None
):
    """Stale non-OpenAI agent provider rows should be rejected before SDK creation."""

    async def scenario() -> None:
        factory = LibrarianClientFactory(
            openai_client_builder=ExplodingOpenAIClientBuilder(),
            dry_run=True,
        )

        for provider_type in ["OPENROUTER", "ANTHROPIC", "HERMES", "LOCAL", "CUSTOM"]:
            result: ProviderClientTestResult = await factory.test_connection(
                provider=_provider(provider_type),
                secret_resolver=StaticSecretResolver(),
                test_query="ping",
            )

            assert result.as_public_dict() == {
                "provider_id": PROVIDER_ID,
                "ok": False,
                "message": (
                    f"provider type {provider_type} is unsupported for librarian SDK clients"
                ),
            }

    anyio.run(scenario)
