"""Behavior tests for OpenAI-only API-key librarian provider SDK client foundation."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import cast

import anyio
from app.connections.application.librarian_service import LibrarianService
from app.connections.domain.contracts.librarian_provider_contracts import (
    LibrarianProviderCreate,
    LibrarianProviderUpdate,
)
from app.connections.domain.entities.read_models import LibrarianProvider
from app.connections.domain.event_enum.provider_enums import AuthType, ProviderType
from app.connections.domain.repositories.librarian_repository import (
    ILibrarianProviderRepository,
    IProviderSecretRepository,
)
from app.connections.infrastructure.librarians.clients import (
    ApiKeyCredential,
    LibrarianClientFactory,
    LibrarianProviderClientFactory,
    ProviderClientTestResult,
    SecretResolver,
)
from app.connections.infrastructure.librarians.openai_adapter import OpenAIClientConfig
from app.shared.types.extra_types import JSONValue
from openai import OpenAI

SECRET_VALUE = "sk-tes...leak"
PROVIDER_ID = "00000000-0000-4000-8000-000000000777"


class RecordingSdkClient:
    """Fake SDK client that records typed constructor config without network I/O."""

    def __init__(self, config: OpenAIClientConfig) -> None:
        """Capture SDK constructor config."""
        self.config = config


class RecordingOpenAIClientBuilder:
    """Callable fake OpenAI SDK builder for assertions at the network boundary."""

    def __init__(self) -> None:
        """Initialize empty call list."""
        self.calls: list[OpenAIClientConfig] = []

    def __call__(self, config: OpenAIClientConfig) -> OpenAI:
        """Record SDK constructor config and return a fake SDK client."""
        self.calls.append(config)
        return cast(OpenAI, RecordingSdkClient(config))


class ExplodingOpenAIClientBuilder:
    """OpenAI SDK builder that fails if construction is attempted."""

    def __call__(self, config: OpenAIClientConfig) -> OpenAI:
        """Raise if client construction is attempted."""
        raise AssertionError(f"SDK client should not instantiate: {config!r}")


class StaticSecretResolver(IProviderSecretRepository):
    """Provider secret resolver test double."""

    def __init__(self, value: str | None) -> None:
        """Store the secret resolution value."""
        self.value = value
        self.resolved: list[tuple[str, str]] = []

    async def resolve(self, provider_id: str, key_name: str) -> str | None:
        """Return configured secret value."""
        self.resolved.append((provider_id, key_name))
        return self.value

    async def set_secret(self, *, provider_id: str, key_name: str, value: str) -> None:
        """Set secret is unused in this test double."""
        raise NotImplementedError

    async def delete_for_provider(self, provider_id: str, key_name: str) -> None:
        """Delete secret is unused in this test double."""
        raise NotImplementedError


class StaticSecretMapResolver(IProviderSecretRepository):
    """Provider secret resolver backed by explicit key values."""

    def __init__(self, secrets: dict[str, str]) -> None:
        """Store explicit secret values by key name."""
        self.secrets = secrets
        self.resolved: list[tuple[str, str]] = []

    async def resolve(self, provider_id: str, key_name: str) -> str | None:
        """Return configured secret value by key name."""
        self.resolved.append((provider_id, key_name))
        return self.secrets.get(key_name)

    async def set_secret(self, *, provider_id: str, key_name: str, value: str) -> None:
        """Set secret is unused in this test double."""
        raise NotImplementedError

    async def delete_for_provider(self, provider_id: str, key_name: str) -> None:
        """Delete secret is unused in this test double."""
        raise NotImplementedError


class FakeProviderRepository(ILibrarianProviderRepository):
    """In-memory provider repository for service wiring behavior."""

    def __init__(self, provider: LibrarianProvider) -> None:
        """Store one provider."""
        self.provider = provider

    async def create(self, payload: LibrarianProviderCreate) -> LibrarianProvider:
        """Create is unused in this test double."""
        raise NotImplementedError

    async def get(self, provider_id: str) -> LibrarianProvider | None:
        """Return the stored provider by id."""
        if provider_id != self.provider.id:
            return None
        return self.provider

    async def list_all(self) -> list[LibrarianProvider]:
        """Return the stored provider."""
        return [self.provider]

    async def update(
        self, provider_id: str, payload: LibrarianProviderUpdate
    ) -> LibrarianProvider:
        """Update is unused in this test double."""
        raise NotImplementedError

    async def delete(self, provider_id: str) -> None:
        """Delete is unused in this test double."""
        raise NotImplementedError


class FakeSecretRepository(IProviderSecretRepository):
    """In-memory secret repository for service wiring behavior."""

    def __init__(self, value: str | None) -> None:
        """Store one API key value."""
        self.value = value

    async def resolve(self, provider_id: str, key_name: str) -> str | None:
        """Resolve a secret by key name."""
        if key_name != "api_key":
            return None
        return self.value

    async def set_secret(self, *, provider_id: str, key_name: str, value: str) -> None:
        """Set secret is unused in this test double."""
        raise NotImplementedError

    async def delete_for_provider(self, provider_id: str, key_name: str) -> None:
        """Delete secret is unused in this test double."""
        raise NotImplementedError


class RecordingClientFactory(LibrarianProviderClientFactory):
    """Client factory fake for LibrarianService boundary wiring."""

    def __init__(self) -> None:
        """Initialize captured call fields."""
        self.provider: LibrarianProvider | None = None
        self.test_query: str | None = None

    async def test_connection(
        self,
        *,
        provider: LibrarianProvider,
        secret_resolver: SecretResolver,
        test_query: str,
    ) -> ProviderClientTestResult:
        """Return deterministic connection result."""
        self.provider = provider
        self.test_query = test_query
        resolved = await secret_resolver.resolve(provider.id, "api_key")
        return ProviderClientTestResult(
            provider_id=provider.id,
            ok=resolved is not None,
            message="fake client factory accepted query",
        )


def _provider(
    *,
    provider_type: str = ProviderType.OPENAI.value,
    auth_type: AuthType = AuthType.API_KEY,
    enabled: bool = True,
    config: dict[str, JSONValue] | None = None,
) -> LibrarianProvider:
    """Build a librarian provider read model."""
    now = datetime(2026, 5, 13, 11, 30, tzinfo=UTC)
    return LibrarianProvider(
        id=PROVIDER_ID,
        name="sdk-backed librarian",
        provider_type=provider_type,
        auth_type=auth_type.value,
        enabled=enabled,
        config={} if config is None else config,
        created_at=now,
        updated_at=now,
    )


def _secret_is_absent_from(value: object) -> bool:
    """Return true when rendered values do not contain the test API key."""
    return SECRET_VALUE not in repr(value) and SECRET_VALUE not in str(value)


def test_connection_uses_official_openai_sdk_for_openai_api_keys() -> None:
    """OPENAI providers should use official OpenAI SDK construction only."""

    async def scenario() -> None:
        openai_client_builder = RecordingOpenAIClientBuilder()
        factory = LibrarianClientFactory(
            openai_client_builder=openai_client_builder,
            dry_run=True,
        )

        result = await factory.test_connection(
            provider=_provider(config={"model": "gpt-5.5"}),
            secret_resolver=StaticSecretResolver(SECRET_VALUE),
            test_query="ping",
        )

        assert result.as_public_dict() == {
            "provider_id": PROVIDER_ID,
            "ok": True,
            "message": "OPENAI SDK client dry-run accepted query",
        }
        assert openai_client_builder.calls == [OpenAIClientConfig(api_key=SECRET_VALUE)]
        assert _secret_is_absent_from(result.as_public_dict())
        assert _secret_is_absent_from(result)

    anyio.run(scenario)


def test_connection_rejects_stale_non_openai_agent_provider_rows() -> None:
    """Removed non-OpenAI agent provider rows should stop before SDK construction."""

    async def scenario() -> None:
        factory = LibrarianClientFactory(
            openai_client_builder=ExplodingOpenAIClientBuilder(),
            dry_run=True,
        )

        for provider_type in ["OPENROUTER", "ANTHROPIC", "HERMES", "LOCAL", "CUSTOM"]:
            result = await factory.test_connection(
                provider=_provider(provider_type=provider_type),
                secret_resolver=StaticSecretResolver(SECRET_VALUE),
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


def test_connection_does_not_instantiate_sdk_when_provider_is_disabled_or_secret_missing() -> (
    None
):
    """Disabled or uncredentialed providers should stop before SDK construction."""

    async def scenario() -> None:
        factory = LibrarianClientFactory(
            openai_client_builder=ExplodingOpenAIClientBuilder(),
            dry_run=True,
        )
        disabled_secret_resolver = StaticSecretResolver(SECRET_VALUE)
        disabled_result = await factory.test_connection(
            provider=_provider(enabled=False),
            secret_resolver=disabled_secret_resolver,
            test_query="ping",
        )
        missing_result = await factory.test_connection(
            provider=_provider(),
            secret_resolver=StaticSecretResolver(None),
            test_query="ping",
        )

        assert disabled_result.as_public_dict() == {
            "provider_id": PROVIDER_ID,
            "ok": False,
            "message": "provider disabled",
        }
        assert disabled_secret_resolver.resolved == []
        assert missing_result.as_public_dict() == {
            "provider_id": PROVIDER_ID,
            "ok": False,
            "message": "api_key missing",
        }

    anyio.run(scenario)


def test_connection_reports_clear_unsupported_auth_for_api_key_only_scope() -> None:
    """OAuth auth should be clear without SDK construction."""

    async def scenario() -> None:
        factory = LibrarianClientFactory(
            openai_client_builder=ExplodingOpenAIClientBuilder(),
            dry_run=True,
        )
        oauth_result = await factory.test_connection(
            provider=_provider(auth_type=AuthType.OAUTH),
            secret_resolver=StaticSecretResolver(SECRET_VALUE),
            test_query="ping",
        )

        assert oauth_result.as_public_dict() == {
            "provider_id": PROVIDER_ID,
            "ok": False,
            "message": "auth type OAUTH is unsupported for API-key SDK clients",
        }

    anyio.run(scenario)


def test_connection_accepts_openai_codex_oauth_credentials_without_token_leak() -> None:
    """OPENAI_CODEX provider tests should validate OAuth secret availability."""

    async def scenario() -> None:
        factory = LibrarianClientFactory(
            openai_client_builder=ExplodingOpenAIClientBuilder(),
            dry_run=True,
        )
        secret_resolver = StaticSecretMapResolver(
            {
                "oauth_access_token": SECRET_VALUE,
                "oauth_expires_at": "2999-01-01T00:00:00+00:00",
            }
        )

        result = await factory.test_connection(
            provider=_provider(
                provider_type=ProviderType.OPENAI_CODEX.value,
                auth_type=AuthType.OAUTH,
            ),
            secret_resolver=secret_resolver,
            test_query="ping",
        )

        assert result.as_public_dict() == {
            "provider_id": PROVIDER_ID,
            "ok": True,
            "message": "OPENAI_CODEX OAuth credentials available",
        }
        assert secret_resolver.resolved == [
            (PROVIDER_ID, "oauth_access_token"),
            (PROVIDER_ID, "oauth_refresh_token"),
            (PROVIDER_ID, "oauth_expires_at"),
        ]
        assert _secret_is_absent_from(result.as_public_dict())

    anyio.run(scenario)


def test_connection_reports_missing_openai_codex_oauth_credentials() -> None:
    """OPENAI_CODEX provider tests should be explicit when tokens are absent."""

    async def scenario() -> None:
        factory = LibrarianClientFactory(
            openai_client_builder=ExplodingOpenAIClientBuilder(),
            dry_run=True,
        )

        result = await factory.test_connection(
            provider=_provider(
                provider_type=ProviderType.OPENAI_CODEX.value,
                auth_type=AuthType.OAUTH,
            ),
            secret_resolver=StaticSecretResolver(None),
            test_query="ping",
        )

        assert result.as_public_dict() == {
            "provider_id": PROVIDER_ID,
            "ok": False,
            "message": "oauth credentials missing",
        }

    anyio.run(scenario)


def test_connection_rejects_openai_codex_oauth_expired_access_token() -> None:
    """OPENAI_CODEX provider tests should not pass stale OAuth access tokens."""

    async def scenario() -> None:
        factory = LibrarianClientFactory(
            openai_client_builder=ExplodingOpenAIClientBuilder(),
            dry_run=True,
        )

        result = await factory.test_connection(
            provider=_provider(
                provider_type=ProviderType.OPENAI_CODEX.value,
                auth_type=AuthType.OAUTH,
            ),
            secret_resolver=StaticSecretMapResolver(
                {
                    "oauth_access_token": SECRET_VALUE,
                    "oauth_refresh_token": "refresh-secret",
                    "oauth_expires_at": "2000-01-01T00:00:00+00:00",
                }
            ),
            test_query="ping",
        )

        assert result.as_public_dict() == {
            "provider_id": PROVIDER_ID,
            "ok": False,
            "message": "oauth access token expired",
        }
        assert _secret_is_absent_from(result.as_public_dict())

    anyio.run(scenario)


def test_connection_rejects_openai_codex_oauth_refresh_only_secret() -> None:
    """OPENAI_CODEX provider tests should not pass refresh-only credentials."""

    async def scenario() -> None:
        factory = LibrarianClientFactory(
            openai_client_builder=ExplodingOpenAIClientBuilder(),
            dry_run=True,
        )

        result = await factory.test_connection(
            provider=_provider(
                provider_type=ProviderType.OPENAI_CODEX.value,
                auth_type=AuthType.OAUTH,
            ),
            secret_resolver=StaticSecretMapResolver(
                {"oauth_refresh_token": "refresh-secret"}
            ),
            test_query="ping",
        )

        assert result.as_public_dict() == {
            "provider_id": PROVIDER_ID,
            "ok": False,
            "message": "oauth access token missing",
        }
        assert _secret_is_absent_from(result.as_public_dict())

    anyio.run(scenario)


def test_connection_rejects_openai_codex_api_key_auth() -> None:
    """OPENAI_CODEX provider tests should keep OAuth-only auth semantics."""

    async def scenario() -> None:
        factory = LibrarianClientFactory(
            openai_client_builder=ExplodingOpenAIClientBuilder(),
            dry_run=True,
        )

        result = await factory.test_connection(
            provider=_provider(provider_type=ProviderType.OPENAI_CODEX.value),
            secret_resolver=StaticSecretResolver(SECRET_VALUE),
            test_query="ping",
        )

        assert result.as_public_dict() == {
            "provider_id": PROVIDER_ID,
            "ok": False,
            "message": "provider type OPENAI_CODEX requires OAUTH auth",
        }

    anyio.run(scenario)


def test_provider_client_result_never_exposes_api_key_value() -> None:
    """Connection result repr, str, and dict should never include credential values."""
    result = ProviderClientTestResult(
        provider_id=PROVIDER_ID,
        ok=True,
        message="dry-run accepted without secret material",
    )

    assert result.as_public_dict() == {
        "provider_id": PROVIDER_ID,
        "ok": True,
        "message": "dry-run accepted without secret material",
    }
    assert _secret_is_absent_from(result.as_public_dict())
    assert _secret_is_absent_from(result)


def test_api_key_credential_repr_never_exposes_api_key_value() -> None:
    """API-key credential wrapper should redact repr and str output."""
    credential = ApiKeyCredential(SECRET_VALUE)

    assert repr(credential) == "ApiKeyCredential(value=***redacted***)"
    assert str(credential) == "ApiKeyCredential(value=***redacted***)"
    assert _secret_is_absent_from(credential)


def test_librarian_service_test_provider_uses_client_factory_without_network() -> None:
    """LibrarianService should delegate provider testing to the client factory abstraction."""

    async def scenario() -> None:
        provider = _provider()
        factory = RecordingClientFactory()
        service = LibrarianService(
            provider_repo=FakeProviderRepository(provider),
            secret_repo=FakeSecretRepository(SECRET_VALUE),
            client_factory=factory,
        )
        result = await service.test_provider(provider.id, test_query="library ping")

        assert result == {
            "provider_id": PROVIDER_ID,
            "ok": True,
            "message": "fake client factory accepted query",
        }
        assert factory.provider == provider
        assert factory.test_query == "library ping"
        assert _secret_is_absent_from(result)

    anyio.run(scenario)
