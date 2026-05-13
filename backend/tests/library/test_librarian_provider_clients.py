"""Behavior tests for API-key librarian provider SDK client foundation."""

from __future__ import annotations

from datetime import UTC, datetime

import anyio
from app.library.application.librarian_service import LibrarianService
from app.library.domain.entities.enums import AuthType, ProviderType
from app.library.domain.entities.read_models import LibrarianProvider
from app.library.domain.repositories.librarian_repository import (
    LibrarianProviderRepository,
    ProviderSecretRepository,
)
from app.library.infrastructure.librarians.clients import (
    LibrarianClientFactory,
    ProviderClientTestResult,
    SecretResolver,
)
from app.shared.types.extra_types import JSONValue

SECRET_VALUE = "sk-test-secret-value-never-leak"
PROVIDER_ID = "00000000-0000-4000-8000-000000000777"


class RecordingSdkClient:
    """Fake SDK client that records construction kwargs without network I/O."""

    def __init__(self, **kwargs: object) -> None:
        """Capture SDK constructor keyword args."""
        self.kwargs = kwargs


class RecordingConstructor:
    """Callable fake SDK constructor for assertions at the network boundary."""

    def __init__(self) -> None:
        """Initialize empty call list."""
        self.calls: list[dict[str, object]] = []

    def __call__(self, **kwargs: object) -> RecordingSdkClient:
        """Record SDK constructor kwargs and return a fake SDK client."""
        self.calls.append(kwargs)
        return RecordingSdkClient(**kwargs)


class ExplodingConstructor:
    """SDK constructor that fails if a disabled or uncredentialed provider instantiates."""

    def __call__(self, **kwargs: object) -> RecordingSdkClient:
        """Raise if client construction is attempted."""
        raise AssertionError(f"SDK client should not instantiate: {kwargs!r}")


class StaticSecretResolver:
    """Provider secret resolver test double."""

    def __init__(self, value: str | None) -> None:
        """Store the secret resolution value."""
        self.value = value
        self.resolved: list[tuple[str, str]] = []

    async def resolve(self, provider_id: str, key_name: str) -> str | None:
        """Return configured secret value."""
        self.resolved.append((provider_id, key_name))
        return self.value


class FakeProviderRepository(LibrarianProviderRepository):
    """In-memory provider repository for service wiring behavior."""

    def __init__(self, provider: LibrarianProvider) -> None:
        """Store one provider."""
        self.provider = provider

    async def create(self, payload: dict[str, JSONValue]) -> LibrarianProvider:
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
        self, provider_id: str, payload: dict[str, JSONValue]
    ) -> LibrarianProvider:
        """Update is unused in this test double."""
        raise NotImplementedError

    async def delete(self, provider_id: str) -> None:
        """Delete is unused in this test double."""
        raise NotImplementedError


class FakeSecretRepository(ProviderSecretRepository):
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


class RecordingClientFactory:
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
    provider_type: ProviderType = ProviderType.OPENAI,
    auth_type: AuthType = AuthType.API_KEY,
    enabled: bool = True,
    config: dict[str, JSONValue] | None = None,
) -> LibrarianProvider:
    """Build a librarian provider read model."""
    now = datetime(2026, 5, 13, 11, 30, tzinfo=UTC)
    return LibrarianProvider(
        id=PROVIDER_ID,
        name="sdk-backed librarian",
        provider_type=provider_type.value,
        auth_type=auth_type.value,
        enabled=enabled,
        config={} if config is None else config,
        created_at=now,
        updated_at=now,
    )


def _secret_is_absent_from(value: object) -> bool:
    """Return true when rendered values do not contain the test API key."""
    return SECRET_VALUE not in repr(value) and SECRET_VALUE not in str(value)


def test_connection_uses_openai_style_sdk_for_openai_and_openrouter_api_keys() -> None:
    """OPENAI and OPENROUTER providers should use OpenAI-style SDK construction."""

    async def scenario() -> None:
        openai_constructor = RecordingConstructor()
        factory = LibrarianClientFactory(
            openai_constructor=openai_constructor,
            anthropic_constructor=ExplodingConstructor(),
            dry_run=True,
        )

        openai_result = await factory.test_connection(
            provider=_provider(config={"model": "gpt-4.1"}),
            secret_resolver=StaticSecretResolver(SECRET_VALUE),
            test_query="ping",
        )
        openrouter_result = await factory.test_connection(
            provider=_provider(
                provider_type=ProviderType.OPENROUTER,
                config={"model": "openai/gpt-4.1"},
            ),
            secret_resolver=StaticSecretResolver(SECRET_VALUE),
            test_query="ping",
        )

        assert openai_result.as_public_dict() == {
            "provider_id": PROVIDER_ID,
            "ok": True,
            "message": "OPENAI SDK client dry-run accepted query",
        }
        assert openrouter_result.as_public_dict() == {
            "provider_id": PROVIDER_ID,
            "ok": True,
            "message": "OPENROUTER SDK client dry-run accepted query",
        }
        assert openai_constructor.calls == [
            {"api_key": SECRET_VALUE},
            {"api_key": SECRET_VALUE, "base_url": "https://openrouter.ai/api/v1"},
        ]
        assert _secret_is_absent_from(openai_result.as_public_dict())
        assert _secret_is_absent_from(openrouter_result.as_public_dict())
        assert _secret_is_absent_from(openai_result)
        assert _secret_is_absent_from(openrouter_result)

    anyio.run(scenario)


def test_connection_uses_anthropic_style_sdk_for_anthropic_api_keys() -> None:
    """ANTHROPIC providers should use Anthropic-style SDK construction."""

    async def scenario() -> None:
        anthropic_constructor = RecordingConstructor()
        factory = LibrarianClientFactory(
            openai_constructor=ExplodingConstructor(),
            anthropic_constructor=anthropic_constructor,
            dry_run=True,
        )

        result = await factory.test_connection(
            provider=_provider(
                provider_type=ProviderType.ANTHROPIC,
                config={"model": "claude-sonnet-4-5"},
            ),
            secret_resolver=StaticSecretResolver(SECRET_VALUE),
            test_query="ping",
        )

        assert result.as_public_dict() == {
            "provider_id": PROVIDER_ID,
            "ok": True,
            "message": "ANTHROPIC SDK client dry-run accepted query",
        }
        assert anthropic_constructor.calls == [{"api_key": SECRET_VALUE}]
        assert _secret_is_absent_from(result.as_public_dict())
        assert _secret_is_absent_from(result)

    anyio.run(scenario)


def test_connection_does_not_instantiate_sdk_when_provider_is_disabled_or_secret_missing() -> (
    None
):
    """Disabled or uncredentialed providers should stop before SDK construction."""

    async def scenario() -> None:
        factory = LibrarianClientFactory(
            openai_constructor=ExplodingConstructor(),
            anthropic_constructor=ExplodingConstructor(),
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


def test_connection_reports_clear_unsupported_provider_and_auth_for_api_key_only_scope() -> (
    None
):
    """Unsupported providers and OAuth auth should be clear without SDK construction."""

    async def scenario() -> None:
        factory = LibrarianClientFactory(
            openai_constructor=ExplodingConstructor(),
            anthropic_constructor=ExplodingConstructor(),
            dry_run=True,
        )

        oauth_result = await factory.test_connection(
            provider=_provider(auth_type=AuthType.OAUTH),
            secret_resolver=StaticSecretResolver(SECRET_VALUE),
            test_query="ping",
        )
        custom_result = await factory.test_connection(
            provider=_provider(provider_type=ProviderType.CUSTOM),
            secret_resolver=StaticSecretResolver(SECRET_VALUE),
            test_query="ping",
        )

        assert oauth_result.as_public_dict() == {
            "provider_id": PROVIDER_ID,
            "ok": False,
            "message": "auth type OAUTH is unsupported for API-key SDK clients",
        }
        assert custom_result.as_public_dict() == {
            "provider_id": PROVIDER_ID,
            "ok": False,
            "message": "provider type CUSTOM is unsupported for librarian SDK clients",
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


def test_librarian_service_test_provider_uses_client_factory_without_network() -> None:
    """LibrarianService should delegate provider testing to the client factory abstraction."""

    async def scenario() -> None:
        provider = _provider(provider_type=ProviderType.ANTHROPIC)
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
