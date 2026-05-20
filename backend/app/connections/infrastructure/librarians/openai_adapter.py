"""OpenAI librarian provider SDK adapter."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from app.connections.domain.event_enum.provider_enums import ProviderType
from app.connections.infrastructure.librarians.contracts import (
    ApiKeyCredential,
    ProviderClientTestResult,
)
from app.shared.exceptions import ConnectionsProviderUnsupportedError
from app.shared.types.extra_types import JSONObject
from openai import OpenAI


@dataclass(frozen=True, slots=True)
class OpenAIClientConfig:
    """Constructor config for the official OpenAI SDK client."""

    api_key: str
    base_url: str | None = None
    default_headers: dict[str, str] | None = None
    timeout: float | None = None


OpenAIClientBuilder = Callable[[OpenAIClientConfig], OpenAI]


@dataclass(frozen=True, slots=True)
class OpenAIStyleSDKAdapter:
    """Adapter for the official OpenAI SDK client."""

    client: OpenAI
    provider_type: ProviderType
    dry_run: bool = True

    async def test_connection(self, test_query: str) -> ProviderClientTestResult:
        """Perform a deterministic default connection test.

        Args:
            test_query: Query text submitted by callers. Default dry-run mode does
                not send it to external services.

        Returns:
            Provider test result.
        """
        _ = test_query
        if self.dry_run:
            result = ProviderClientTestResult(
                provider_id="",
                ok=True,
                message=f"{self.provider_type.value} SDK client dry-run accepted query",
            )
            return result
        result = ProviderClientTestResult(
            provider_id="",
            ok=False,
            message="live SDK connection tests are not enabled",
        )
        return result


def build_openai_client_config(
    provider_type: ProviderType,
    config: JSONObject,
    credential: ApiKeyCredential,
) -> OpenAIClientConfig:
    """Build constructor config for the official OpenAI SDK client.

    Args:
        provider_type: Provider type requested by the caller.
        config: Provider config payload. OpenAI currently requires no config keys.
        credential: Redacted API-key credential.

    Returns:
        OpenAIClientConfig: Official OpenAI SDK constructor config.
    """
    _ = config
    if provider_type is not ProviderType.OPENAI:
        raise ConnectionsProviderUnsupportedError(
            f"provider type {provider_type.value} is unsupported for OpenAI SDK clients"
        )
    client_config = OpenAIClientConfig(api_key=credential.value)
    return client_config


def build_openai_client(config: OpenAIClientConfig) -> OpenAI:
    """Construct the official OpenAI SDK client.

    Args:
        config: Official OpenAI SDK constructor config.

    Returns:
        OpenAI: Official OpenAI SDK client.
    """
    client = OpenAI(
        api_key=config.api_key,
        base_url=config.base_url,
        default_headers=config.default_headers,
        timeout=config.timeout,
    )
    return client
