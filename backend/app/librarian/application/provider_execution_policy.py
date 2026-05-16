"""Execution-readiness policy for librarian providers."""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime

from app.connections.domain.entities.read_models import LibrarianProvider
from app.connections.domain.event_enum.provider_enums import (
    AuthType,
    ProviderSecretKey,
    ProviderType,
)
from app.connections.domain.repositories.librarian_repository import (
    IProviderSecretRepository,
)
from app.shared.types.types_convert_utils import now_utc


async def provider_can_execute(
    provider: LibrarianProvider,
    secret_repo: IProviderSecretRepository,
    now_provider: Callable[[], datetime] = now_utc,
) -> bool:
    """Return whether a provider has enough credential material to execute.

    Args:
        provider: Provider metadata row.
        secret_repo: Provider secret repository.
        now_provider: Clock boundary for deterministic tests.

    Returns:
        bool: ``True`` when the provider can execute or refresh a request.
    """
    if not provider.enabled:
        return False
    provider_shape = _provider_shape(provider)
    if provider_shape is None:
        return False
    provider_type, auth_type = provider_shape
    if provider_type is ProviderType.OPENAI and auth_type is AuthType.API_KEY:
        return await _has_secret(secret_repo, provider.id, ProviderSecretKey.API_KEY)
    if provider_type is ProviderType.OPENAI_CODEX and auth_type is AuthType.OAUTH:
        return await _has_oauth_execution_secret(provider, secret_repo, now_provider)
    return False


async def _has_oauth_execution_secret(
    provider: LibrarianProvider,
    secret_repo: IProviderSecretRepository,
    now_provider: Callable[[], datetime],
) -> bool:
    refresh_token = await _resolve_secret(
        secret_repo,
        provider.id,
        ProviderSecretKey.OAUTH_REFRESH_TOKEN,
    )
    if refresh_token is not None:
        return True
    access_token = await _resolve_secret(
        secret_repo,
        provider.id,
        ProviderSecretKey.OAUTH_ACCESS_TOKEN,
    )
    if access_token is None:
        return False
    expires_at = _parse_datetime(
        await _resolve_secret(
            secret_repo,
            provider.id,
            ProviderSecretKey.OAUTH_EXPIRES_AT,
        )
    )
    if expires_at is None:
        return False
    current = _aware_now(now_provider)
    return expires_at > current


async def _has_secret(
    secret_repo: IProviderSecretRepository,
    provider_id: str,
    key: ProviderSecretKey,
) -> bool:
    value = await _resolve_secret(secret_repo, provider_id, key)
    return value is not None


async def _resolve_secret(
    secret_repo: IProviderSecretRepository,
    provider_id: str,
    key: ProviderSecretKey,
) -> str | None:
    value = await secret_repo.resolve(provider_id, key.value)
    if value is None or value == "":
        return None
    return value


def _provider_shape(
    provider: LibrarianProvider,
) -> tuple[ProviderType, AuthType] | None:
    if not isinstance(provider.provider_type, ProviderType) or not isinstance(
        provider.auth_type, AuthType
    ):
        return None
    return provider.provider_type, provider.auth_type


def _parse_datetime(value: str | None) -> datetime | None:
    if value is None:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed


def _aware_now(now_provider: Callable[[], datetime]) -> datetime:
    current = now_provider()
    if current.tzinfo is None:
        return current.replace(tzinfo=UTC)
    return current
