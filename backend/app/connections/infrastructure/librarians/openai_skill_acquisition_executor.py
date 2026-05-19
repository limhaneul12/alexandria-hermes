"""Provider-backed OpenAI/Codex skill-acquisition executor."""

from __future__ import annotations

import base64
import json
import logging
from datetime import UTC, datetime
from typing import cast

import anyio
from app.connections.domain.entities.read_models import LibrarianProvider
from app.connections.domain.event_enum.provider_enums import (
    AuthType,
    ProviderSecretKey,
    ProviderType,
)
from app.connections.domain.repositories.librarian_repository import (
    ILibrarianProviderRepository,
    IProviderSecretRepository,
)
from app.connections.infrastructure.librarians.openai_adapter import (
    OpenAIClientBuilder,
    OpenAIClientConfig,
    build_openai_client,
)
from app.connections.infrastructure.librarians.openai_skill_acquisition_artifact_parser import (
    skill_acquisition_artifact_from_provider_text,
)
from app.connections.infrastructure.librarians.provider_types import (
    parse_auth_type,
    parse_provider_type,
)
from app.librarian.application.skill_acquisition_runner import (
    SkillAcquisitionExecutionRequest,
)
from app.librarian.domain.contracts.skill_acquisition_contracts import (
    SkillAcquisitionArtifact,
)
from app.shared.exceptions.librarian_exceptions import (
    LibrarianSkillAcquisitionExecutionError,
    LibrarianSkillAcquisitionProviderError,
)
from app.shared.types.extra_types import JSONValue
from app.shared.types.types_convert_utils import now_utc
from openai import OpenAI, OpenAIError
from openai.types.responses import ResponseTextDeltaEvent

_DEFAULT_MODEL = "gpt-5.5"
_DEFAULT_INSTRUCTIONS = """
Return only strict JSON with these fields:
title, purpose, content, summary, tags, required_tools, evidence_urls,
source_summary, next_steps, risk_level, version, activate, status.
Do not include markdown fences, explanations, or extra prose.
""".strip()
_CODEX_BASE_URL = "https://chatgpt.com/backend-api/codex"
_CODEX_USER_AGENT = "codex_cli_rs/0.0.0 (Alexandria Hermes)"
_CODEX_ORIGINATOR = "codex_cli_rs"
logger = logging.getLogger(__name__)


class OpenAISkillAcquisitionExecutor:
    """Execute skill-acquisition prompts via OpenAI-style provider responses API."""

    def __init__(
        self,
        *,
        provider_repo: ILibrarianProviderRepository,
        secret_repo: IProviderSecretRepository,
        openai_client_builder: OpenAIClientBuilder = build_openai_client,
    ) -> None:
        """Initialize provider-backed skill-acquisition executor.

        Args:
            provider_repo: Provider metadata repository.
            secret_repo: Provider secret resolver.
            openai_client_builder: SDK client builder boundary.
        """
        self.provider_repo = provider_repo
        self.secret_repo = secret_repo
        self.openai_client_builder = openai_client_builder

    async def acquire_skill(
        self,
        request: SkillAcquisitionExecutionRequest,
    ) -> SkillAcquisitionArtifact:
        """Acquire one skill artifact from a configured provider.

        Args:
            request: Normalized acquisition request.

        Returns:
            Parsed and validated skill artifact.
        """
        provider = await self._resolve_provider(request)
        provider_type = _parse_provider_type(provider)
        auth_type = _parse_auth_type(provider)
        client_config = await self._client_config(provider, provider_type, auth_type)
        if client_config is None:
            raise LibrarianSkillAcquisitionProviderError(
                "Provider credentials unavailable for skill acquisition"
            )

        client = self.openai_client_builder(client_config)
        model = _model_for_provider(provider)
        instructions = _acquisition_instructions()
        try:
            if provider_type is ProviderType.OPENAI_CODEX:
                summary = await anyio.to_thread.run_sync(
                    _create_codex_stream_summary,
                    client,
                    model,
                    request.prompt,
                    instructions,
                )
            else:
                response = client.responses.create(
                    model=model,
                    input=request.prompt,
                    instructions=instructions,
                )
                summary = response.output_text
        except OpenAIError as error:
            _log_provider_execution_failure(
                provider_id=provider.id,
                provider_type=provider_type,
                error=error,
            )
            raise LibrarianSkillAcquisitionExecutionError(
                "Skill acquisition execution failed"
            ) from error

        return skill_acquisition_artifact_from_provider_text(summary)

    async def _resolve_provider(
        self,
        request: SkillAcquisitionExecutionRequest,
    ) -> LibrarianProvider:
        """Resolve provider id and ensure it exists.

        Args:
            request: Execution request that references a provider.

        Returns:
            Matching provider read model.
        """
        if request.provider_id is None:
            raise LibrarianSkillAcquisitionProviderError(
                "Skill acquisition requires a provider id"
            )
        provider = await self.provider_repo.get(request.provider_id)
        if provider is None:
            raise LibrarianSkillAcquisitionProviderError(
                "Provider not found for skill acquisition"
            )
        return provider

    async def _client_config(
        self,
        provider: LibrarianProvider,
        provider_type: ProviderType | None,
        auth_type: AuthType,
    ) -> OpenAIClientConfig | None:
        if provider_type is ProviderType.OPENAI and auth_type is AuthType.API_KEY:
            api_key = await self.secret_repo.resolve(
                provider.id,
                ProviderSecretKey.API_KEY.value,
            )
            if not api_key:
                return None
            return OpenAIClientConfig(api_key=api_key)

        if provider_type is ProviderType.OPENAI_CODEX and auth_type is AuthType.OAUTH:
            return await self._codex_client_config(provider.id)

        return None

    async def _codex_client_config(
        self,
        provider_id: str,
    ) -> OpenAIClientConfig | None:
        access_token = await self.secret_repo.resolve(
            provider_id,
            ProviderSecretKey.OAUTH_ACCESS_TOKEN.value,
        )
        if not access_token:
            return None
        expires_at_value = await self.secret_repo.resolve(
            provider_id,
            ProviderSecretKey.OAUTH_EXPIRES_AT.value,
        )
        expires_at = _parse_expires_at(expires_at_value)
        if expires_at is not None and expires_at <= now_utc():
            return None
        return OpenAIClientConfig(
            api_key=access_token,
            base_url=_CODEX_BASE_URL,
            default_headers=_codex_default_headers(access_token),
        )


def _parse_provider_type(provider: LibrarianProvider) -> ProviderType:
    provider_type = parse_provider_type(provider.provider_type)
    if provider_type not in {ProviderType.OPENAI, ProviderType.OPENAI_CODEX}:
        raise LibrarianSkillAcquisitionProviderError(
            "Provider type is unsupported for skill acquisition"
        )
    return provider_type


def _parse_auth_type(provider: LibrarianProvider) -> AuthType:
    try:
        auth_type = parse_auth_type(provider.auth_type)
    except ValueError as error:
        raise LibrarianSkillAcquisitionProviderError(
            "Provider auth type is unsupported for skill acquisition"
        ) from error
    if auth_type not in {AuthType.API_KEY, AuthType.OAUTH}:
        raise LibrarianSkillAcquisitionProviderError(
            "Provider auth type is unsupported for skill acquisition"
        )
    return auth_type


def _model_for_provider(provider: LibrarianProvider) -> str:
    model = _string_config_value(provider.config.get("model"))
    if model is None:
        return _DEFAULT_MODEL
    return model


def _string_config_value(value: JSONValue | None) -> str | None:
    if not isinstance(value, str):
        return None
    stripped = value.strip()
    if not stripped:
        return None
    return stripped


def _acquisition_instructions() -> str:
    return _DEFAULT_INSTRUCTIONS


def _create_codex_stream_summary(
    client: OpenAI,
    model: str,
    prompt: str,
    instructions: str,
) -> str:
    stream = client.responses.create(
        model=model,
        input=[{"role": "user", "content": prompt}],
        instructions=instructions,
        store=False,
        stream=True,
    )
    text_parts = [
        event.delta for event in stream if isinstance(event, ResponseTextDeltaEvent)
    ]
    return "".join(text_parts).strip()


def _log_provider_execution_failure(
    *,
    provider_id: str,
    provider_type: ProviderType | None,
    error: OpenAIError,
) -> None:
    logger.warning(
        "Skill acquisition provider execution failed",
        extra={
            "provider_id": provider_id,
            "provider_type": None if provider_type is None else provider_type.value,
            "error_type": type(error).__name__,
        },
    )


def _parse_expires_at(value: str | None) -> datetime | None:
    if value is None:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed


def _codex_default_headers(access_token: str) -> dict[str, str]:
    headers = {
        "User-Agent": _CODEX_USER_AGENT,
        "originator": _CODEX_ORIGINATOR,
    }
    account_id = _chatgpt_account_id(access_token)
    if account_id is not None:
        headers["ChatGPT-Account-ID"] = account_id
    return headers


def _chatgpt_account_id(access_token: str) -> str | None:
    parts = access_token.split(".")
    if len(parts) < 2:
        return None
    payload = _decode_jwt_payload(parts[1])
    if payload is None:
        return None
    auth_claim = payload.get("https://api.openai.com/auth")
    if not isinstance(auth_claim, dict):
        return None
    account_id = auth_claim.get("chatgpt_account_id")
    if not isinstance(account_id, str):
        return None
    stripped = account_id.strip()
    if not stripped:
        return None
    return stripped


def _decode_jwt_payload(payload: str) -> dict[str, JSONValue] | None:
    try:
        padded = payload + "=" * (-len(payload) % 4)
        raw_payload = base64.urlsafe_b64decode(padded.encode())
        decoded = json.loads(raw_payload)
    except (ValueError, json.JSONDecodeError):
        return None
    if not isinstance(decoded, dict):
        return None
    return cast(dict[str, JSONValue], decoded)
