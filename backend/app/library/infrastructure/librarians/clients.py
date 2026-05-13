"""SDK-backed API-key client foundation for librarian providers."""

from __future__ import annotations

import importlib
from collections.abc import Callable
from dataclasses import dataclass
from typing import Protocol, cast, runtime_checkable

from app.library.domain.entities.enums import AuthType, ProviderType
from app.library.domain.entities.read_models import LibrarianProvider
from app.shared.exceptions import UnsupportedProviderError
from app.shared.types.extra_types import JSONValue

SDKClientConstructor = Callable[..., object]


@runtime_checkable
class SecretResolver(Protocol):
    """Protocol for resolving provider secrets without exposing secret values."""

    async def resolve(self, provider_id: str, key_name: str) -> str | None:
        """Resolve one provider secret value by key name."""


@runtime_checkable
class LibrarianProviderClientFactory(Protocol):
    """Protocol for deterministic librarian provider connection testing."""

    async def test_connection(
        self,
        *,
        provider: LibrarianProvider,
        secret_resolver: SecretResolver,
        test_query: str,
    ) -> ProviderClientTestResult:
        """Test one provider connection without exposing credentials."""


@dataclass(frozen=True, slots=True, repr=False)
class ApiKeyCredential:
    """Redacted API-key credential wrapper.

    Args:
        value: Raw API key value. The value is intentionally excluded from repr/str.
    """

    value: str

    def __repr__(self) -> str:
        """Return a redacted representation."""
        return "ApiKeyCredential(value=***redacted***)"

    __str__ = __repr__


@dataclass(frozen=True, slots=True)
class ProviderClientTestResult:
    """Public provider test result that never carries credential material."""

    provider_id: str
    ok: bool
    message: str

    def as_public_dict(self) -> dict[str, JSONValue]:
        """Return the API-safe response dictionary.

        Args:
            None.

        Return:
            Public test result payload without credentials.
        """
        return {
            "provider_id": self.provider_id,
            "ok": self.ok,
            "message": self.message,
        }


@dataclass(frozen=True, slots=True)
class OpenAIStyleSDKAdapter:
    """Adapter for SDKs that expose an OpenAI-compatible constructor."""

    client: object
    provider_type: ProviderType
    dry_run: bool = True

    async def test_connection(self, test_query: str) -> ProviderClientTestResult:
        """Perform a deterministic default connection test.

        Args:
            test_query: Query text submitted by callers. Default dry-run mode does
                not send it to external services.

        Return:
            Provider test result.
        """
        _ = test_query
        if self.dry_run:
            return ProviderClientTestResult(
                provider_id="",
                ok=True,
                message=f"{self.provider_type.value} SDK client dry-run accepted query",
            )
        return ProviderClientTestResult(
            provider_id="",
            ok=False,
            message="live SDK connection tests are not enabled",
        )


@dataclass(frozen=True, slots=True)
class AnthropicStyleSDKAdapter:
    """Adapter for SDKs that expose an Anthropic-compatible constructor."""

    client: object
    provider_type: ProviderType
    dry_run: bool = True

    async def test_connection(self, test_query: str) -> ProviderClientTestResult:
        """Perform a deterministic default connection test.

        Args:
            test_query: Query text submitted by callers. Default dry-run mode does
                not send it to external services.

        Return:
            Provider test result.
        """
        _ = test_query
        if self.dry_run:
            return ProviderClientTestResult(
                provider_id="",
                ok=True,
                message=f"{self.provider_type.value} SDK client dry-run accepted query",
            )
        return ProviderClientTestResult(
            provider_id="",
            ok=False,
            message="live SDK connection tests are not enabled",
        )


@dataclass(frozen=True, slots=True)
class LibrarianClientFactory:
    """Factory for API-key SDK-backed librarian provider adapters.

    Args:
        openai_constructor: Optional injected OpenAI-compatible SDK constructor.
        anthropic_constructor: Optional injected Anthropic-compatible SDK constructor.
        dry_run: When true, adapters instantiate SDK clients but do not perform
            network requests. This keeps default tests deterministic.
    """

    openai_constructor: SDKClientConstructor | None = None
    anthropic_constructor: SDKClientConstructor | None = None
    dry_run: bool = True

    async def test_connection(
        self,
        *,
        provider: LibrarianProvider,
        secret_resolver: SecretResolver,
        test_query: str,
    ) -> ProviderClientTestResult:
        """Build the correct SDK adapter and run a deterministic connection test.

        Args:
            provider: Librarian provider configuration.
            secret_resolver: Secret resolver boundary for API keys.
            test_query: Caller-provided test query.

        Return:
            Public test result without credential material.
        """
        if not provider.enabled:
            return ProviderClientTestResult(
                provider_id=provider.id,
                ok=False,
                message="provider disabled",
            )

        auth_type = _parse_auth_type(provider.auth_type)
        if auth_type is not AuthType.API_KEY:
            return ProviderClientTestResult(
                provider_id=provider.id,
                ok=False,
                message=(
                    f"auth type {provider.auth_type} is unsupported for "
                    "API-key SDK clients"
                ),
            )

        provider_type = _parse_provider_type(provider.provider_type)
        if provider_type not in {
            ProviderType.OPENAI,
            ProviderType.OPENROUTER,
            ProviderType.ANTHROPIC,
        }:
            return ProviderClientTestResult(
                provider_id=provider.id,
                ok=False,
                message=(
                    f"provider type {provider.provider_type} is unsupported for "
                    "librarian SDK clients"
                ),
            )

        api_key = await secret_resolver.resolve(provider.id, "api_key")
        if not api_key:
            return ProviderClientTestResult(
                provider_id=provider.id,
                ok=False,
                message="api_key missing",
            )

        credential = ApiKeyCredential(api_key)
        try:
            adapter = self._build_adapter(provider_type, provider.config, credential)
        except UnsupportedProviderError as exc:
            return ProviderClientTestResult(
                provider_id=provider.id,
                ok=False,
                message=str(exc),
            )
        result = await adapter.test_connection(test_query)
        return ProviderClientTestResult(
            provider_id=provider.id,
            ok=result.ok,
            message=result.message,
        )

    def _build_adapter(
        self,
        provider_type: ProviderType,
        config: dict[str, JSONValue],
        credential: ApiKeyCredential,
    ) -> OpenAIStyleSDKAdapter | AnthropicStyleSDKAdapter:
        """Build an SDK adapter for the provider type."""
        if provider_type in {ProviderType.OPENAI, ProviderType.OPENROUTER}:
            constructor = self.openai_constructor or _load_openai_constructor()
            kwargs = _openai_style_kwargs(provider_type, config, credential)
            return OpenAIStyleSDKAdapter(
                client=constructor(**kwargs),
                provider_type=provider_type,
                dry_run=self.dry_run,
            )
        constructor = self.anthropic_constructor or _load_anthropic_constructor()
        return AnthropicStyleSDKAdapter(
            client=constructor(api_key=credential.value),
            provider_type=provider_type,
            dry_run=self.dry_run,
        )


def _parse_provider_type(value: str) -> ProviderType:
    """Parse provider type with a clear unsupported fallback."""
    try:
        return ProviderType(value)
    except ValueError:
        return ProviderType.CUSTOM


def _parse_auth_type(value: str) -> AuthType:
    """Parse auth type with a clear unsupported fallback."""
    try:
        return AuthType(value)
    except ValueError:
        return AuthType.NONE


def _openai_style_kwargs(
    provider_type: ProviderType,
    config: dict[str, JSONValue],
    credential: ApiKeyCredential,
) -> dict[str, object]:
    """Build constructor kwargs for OpenAI-compatible SDK clients."""
    kwargs: dict[str, object] = {"api_key": credential.value}
    base_url = config.get("base_url")
    if provider_type is ProviderType.OPENROUTER and base_url is None:
        base_url = "https://openrouter.ai/api/v1"
    if isinstance(base_url, str) and base_url:
        kwargs["base_url"] = base_url
    return kwargs


def _load_openai_constructor() -> SDKClientConstructor:
    """Load the official OpenAI SDK constructor lazily."""
    try:
        module = importlib.import_module("openai")
    except ImportError as exc:
        raise UnsupportedProviderError(
            "OPENAI/OPENROUTER providers require the openai SDK package"
        ) from exc
    constructor = module.__dict__.get("OpenAI")
    if not callable(constructor):
        raise UnsupportedProviderError(
            "OPENAI/OPENROUTER providers require the openai.OpenAI SDK client"
        )
    return cast(SDKClientConstructor, constructor)


def _load_anthropic_constructor() -> SDKClientConstructor:
    """Load the official Anthropic SDK constructor lazily."""
    try:
        module = importlib.import_module("anthropic")
    except ImportError as exc:
        raise UnsupportedProviderError(
            "ANTHROPIC providers require the anthropic SDK package"
        ) from exc
    constructor = module.__dict__.get("Anthropic")
    if not callable(constructor):
        raise UnsupportedProviderError(
            "ANTHROPIC providers require the anthropic.Anthropic SDK client"
        )
    return cast(SDKClientConstructor, constructor)
