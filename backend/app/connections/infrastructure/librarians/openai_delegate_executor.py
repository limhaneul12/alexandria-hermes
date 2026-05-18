"""Provider-backed OpenAI/Codex librarian delegate executor."""

from __future__ import annotations

import base64
import json
import logging
from dataclasses import replace
from datetime import UTC, datetime
from typing import cast

import anyio
from app.connections.domain.event_enum.provider_enums import (
    AuthType,
    ProviderSecretKey,
    ProviderType,
)
from app.connections.domain.repositories.librarian_repository import (
    IProviderSecretRepository,
)
from app.connections.infrastructure.librarians.openai_adapter import (
    OpenAIClientBuilder,
    OpenAIClientConfig,
    build_openai_client,
)
from app.connections.infrastructure.librarians.provider_types import (
    parse_auth_type,
    parse_provider_type,
)
from app.librarian.application.delegate_execution import (
    LibrarianDelegateExecutor,
    LibrarianExecutionPlan,
)
from app.librarian.domain.contracts.hermes_collaboration_contracts import (
    HermesLibrarianAskCommand,
    LibrarianDelegateResult,
)
from app.librarian.domain.event_enum.collaboration_enums import LibrarianDelegateStatus
from app.shared.types.extra_types import JSONValue
from openai import OpenAI, OpenAIError
from openai.types.responses import ResponseTextDeltaEvent

_DEFAULT_MODEL = "gpt-5.5"
_LIBRARIAN_SYSTEM_RULE = """
You are Alexandria Librarian, the librarian for Alexandria-Hermes.
Your purpose is to help Hermes and the user find, evaluate, and apply durable
library assets: skills, prompts, Context Vault memories, decisions, handoffs,
research notes, prior usage, and source references.

Operating rules:
- Act as a librarian and evidence guide, not as a generic chat assistant.
- Prefer concise, actionable answers grounded in the prompt and available brief.
- Do not invent library contents, source refs, tool results, or prior decisions.
- If context is missing, say what is missing and recommend the smallest useful
  fetch/search/recall step.
- Never expose secrets, API keys, OAuth tokens, refresh tokens, Authorization
  headers, connection strings, or operator keys.
- Separate answer, evidence/source refs, gaps, and recommended next actions when
  the prompt asks for analysis.
- When the user asks count/list/inventory questions such as "how many skills",
  answer with the total count first, then show only the top 5 representative
  matches by default as a numbered list with title/type/short reason when those
  fields are available.
- Do not dump the full inventory unless the user explicitly asks for the full
  list or a larger limit; explain that the remaining results can be continued or
  expanded in natural product language.
- Do not expose raw API routes, backend endpoints, frontend paths, headers, or
  implementation-only identifiers in ordinary user answers unless the user
  explicitly asks for API/endpoint details.
- Do not answer inventory questions with only a vague relevance summary; include
  the concrete visible list used for the count, or state that a fetch/search step
  is required before the count can be trusted.
""".strip()
_DEFAULT_INSTRUCTIONS = "Return concise implementation guidance."
_CODEX_BASE_URL = "https://chatgpt.com/backend-api/codex"
_CODEX_USER_AGENT = "codex_cli_rs/0.0.0 (Alexandria Hermes)"
_CODEX_ORIGINATOR = "codex_cli_rs"
logger = logging.getLogger(__name__)


class OpenAIProviderDelegateExecutor(LibrarianDelegateExecutor):
    """Execute librarian delegate prompts through OpenAI-style providers."""

    def __init__(
        self,
        *,
        secret_repo: IProviderSecretRepository,
        openai_client_builder: OpenAIClientBuilder = build_openai_client,
    ) -> None:
        """Initialize the provider-backed executor.

        Args:
            secret_repo: Provider secret resolver boundary.
            openai_client_builder: SDK client constructor boundary.
        """
        self.secret_repo = secret_repo
        self.openai_client_builder = openai_client_builder

    async def execute(
        self,
        *,
        command: HermesLibrarianAskCommand,
        plan: LibrarianExecutionPlan,
        fallback: LibrarianDelegateResult,
    ) -> LibrarianDelegateResult:
        """Execute one delegate plan with an OpenAI-compatible Responses API.

        Args:
            command: Ask-librarian command carrying the prompt.
            plan: Resolved provider/profile execution plan.
            fallback: Safe deterministic result used when execution is unavailable.

        Returns:
            LibrarianDelegateResult: Provider-backed result or safe fallback.
        """
        if plan.provider is None:
            return fallback
        provider_type = parse_provider_type(plan.provider.provider_type)
        auth_type = parse_auth_type(plan.provider.auth_type)
        client_config = await self._client_config(
            provider_id=plan.provider.id,
            provider_type=provider_type,
            auth_type=auth_type,
        )
        if client_config is None:
            return _skipped_result(fallback, "Provider credentials unavailable")

        client = self.openai_client_builder(client_config)
        model = _model_for_plan(plan)
        instructions = _instructions_for_plan(plan)
        try:
            if provider_type is ProviderType.OPENAI_CODEX:
                summary = await anyio.to_thread.run_sync(
                    _create_codex_stream_summary,
                    client,
                    model,
                    _delegate_prompt(command),
                    instructions,
                )
            else:
                response = client.responses.create(
                    model=model,
                    input=_delegate_prompt(command),
                    instructions=instructions,
                )
                summary = response.output_text.strip()
        except OpenAIError as error:
            _log_provider_execution_failure(
                provider_id=plan.provider.id,
                provider_type=provider_type,
                error=error,
            )
            return _skipped_result(fallback, "Provider execution failed")
        if not summary:
            return _skipped_result(fallback, "Provider returned an empty response")
        return replace(
            fallback,
            status=LibrarianDelegateStatus.COMPLETED,
            summary=summary,
        )

    async def _client_config(
        self,
        *,
        provider_id: str,
        provider_type: ProviderType | None,
        auth_type: AuthType,
    ) -> OpenAIClientConfig | None:
        if provider_type is ProviderType.OPENAI and auth_type is AuthType.API_KEY:
            api_key = await self.secret_repo.resolve(
                provider_id,
                ProviderSecretKey.API_KEY.value,
            )
            if not api_key:
                return None
            return OpenAIClientConfig(api_key=api_key)
        if provider_type is ProviderType.OPENAI_CODEX and auth_type is AuthType.OAUTH:
            return await self._codex_client_config(provider_id)
        return None

    async def _codex_client_config(self, provider_id: str) -> OpenAIClientConfig | None:
        access_token = await self.secret_repo.resolve(
            provider_id,
            ProviderSecretKey.OAUTH_ACCESS_TOKEN.value,
        )
        expires_at_value = await self.secret_repo.resolve(
            provider_id,
            ProviderSecretKey.OAUTH_EXPIRES_AT.value,
        )
        if not access_token:
            return None
        expires_at = _parse_expires_at(expires_at_value)
        if expires_at is not None and expires_at <= datetime.now(UTC):
            return None
        return OpenAIClientConfig(
            api_key=access_token,
            base_url=_CODEX_BASE_URL,
            default_headers=_codex_default_headers(access_token),
        )


def _delegate_prompt(command: HermesLibrarianAskCommand) -> str:
    packet = command.librarian_brief
    if packet is None or not packet.strip():
        return command.prompt
    return packet


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
        "Librarian delegate provider execution failed",
        extra={
            "provider_id": provider_id,
            "provider_type": None if provider_type is None else provider_type.value,
            "error_type": type(error).__name__,
        },
    )


def _instructions_for_plan(plan: LibrarianExecutionPlan) -> str:
    role_prompt = _string_config_value(plan.resolution.librarian_role_prompt)
    if role_prompt is None:
        role_prompt = _DEFAULT_INSTRUCTIONS
    return f"{_LIBRARIAN_SYSTEM_RULE}\n\nTask-specific librarian role guidance:\n{role_prompt}"


def _model_for_plan(plan: LibrarianExecutionPlan) -> str:
    if plan.resolution.librarian_model is not None:
        return plan.resolution.librarian_model
    if plan.provider is None:
        return _DEFAULT_MODEL
    model = _string_config_value(plan.provider.config.get("model"))
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


def _skipped_result(
    fallback: LibrarianDelegateResult,
    summary: str,
) -> LibrarianDelegateResult:
    return replace(
        fallback,
        status=LibrarianDelegateStatus.SKIPPED,
        summary=summary,
    )
