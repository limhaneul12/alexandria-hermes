"""OpenAI/Codex skill-acquisition executor tests."""

from __future__ import annotations

import base64
import json
from datetime import UTC, datetime, timedelta
from typing import cast

import anyio
import pytest
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
)
from app.connections.infrastructure.librarians.openai_skill_acquisition_executor import (
    OpenAISkillAcquisitionExecutor,
)
from app.librarian.application.skill_acquisition_runner import (
    SkillAcquisitionExecutionRequest,
)
from app.shared.exceptions.librarian_exceptions import (
    LibrarianSkillAcquisitionArtifactError,
    LibrarianSkillAcquisitionExecutionError,
    LibrarianSkillAcquisitionProviderError,
)
from app.shared.types.extra_types import JSONValue
from openai import OpenAIError
from openai.types.responses import ResponseTextDeltaEvent


class FakeProviderRepository:
    """In-memory provider repository fake."""

    def __init__(self, providers: list[LibrarianProvider]) -> None:
        self.providers = {provider.id: provider for provider in providers}

    async def get(self, provider_id: str) -> LibrarianProvider | None:
        """Return one fake provider by id."""
        return self.providers.get(provider_id)

    async def create(self, payload):  # type: ignore[no-untyped-def]
        """Unused by these tests."""
        raise NotImplementedError

    async def list_all(self) -> list[LibrarianProvider]:
        """Unused by these tests."""
        raise NotImplementedError

    async def update(self, provider_id: str, payload):  # type: ignore[no-untyped-def]
        """Unused by these tests."""
        raise NotImplementedError

    async def delete(self, provider_id: str) -> None:
        """Unused by these tests."""
        raise NotImplementedError


class FakeSecretRepository:
    """In-memory secret repository fake."""

    def __init__(self, values: dict[tuple[str, str], str]) -> None:
        self.values = values

    async def resolve(self, provider_id: str, key_name: str) -> str | None:
        """Resolve one fake secret."""
        return self.values.get((provider_id, key_name))

    async def set_secret(self, *, provider_id: str, key_name: str, value: str) -> None:
        """Unused by these tests."""
        raise NotImplementedError

    async def delete_for_provider(self, provider_id: str, key_name: str) -> None:
        """Unused by these tests."""
        raise NotImplementedError


class FakeResponse:
    """Minimal SDK response carrying output_text."""

    def __init__(self, output_text: str) -> None:
        self.output_text = output_text


class FakeResponsesResource:
    """Minimal SDK responses resource."""

    def __init__(self, output_text: str) -> None:
        self.calls: list[dict[str, JSONValue]] = []
        self.output_text = output_text

    def create(
        self,
        *,
        model: str,
        input: str | list[dict[str, JSONValue]],
        instructions: str,
        store: bool | None = None,
        stream: bool = False,
    ) -> FakeResponse | list[ResponseTextDeltaEvent]:
        self.calls.append(
            {
                "model": model,
                "input": input,
                "instructions": instructions,
                "store": store,
                "stream": stream,
            }
        )
        if stream:
            return [
                ResponseTextDeltaEvent(
                    content_index=0,
                    delta=self.output_text,
                    item_id="item-1",
                    logprobs=[],
                    output_index=0,
                    sequence_number=1,
                    type="response.output_text.delta",
                ),
            ]
        return FakeResponse(self.output_text)


class FakeOpenAIClient:
    """Minimal SDK client with responses.create."""

    def __init__(self, output_text: str) -> None:
        self.responses = FakeResponsesResource(output_text)


class FailingResponsesResource:
    """SDK responses fake that raises a provider error."""

    def create(
        self,
        *,
        model: str,
        input: str | list[dict[str, JSONValue]],
        instructions: str,
        store: bool | None = None,
        stream: bool = False,
    ) -> FakeResponse | list[ResponseTextDeltaEvent]:
        raise OpenAIError("provider failed with token SECRET-TOKEN")


class FailingOpenAIClient:
    """SDK client fake for provider failure paths."""

    def __init__(self) -> None:
        self.responses = FailingResponsesResource()


def _provider(
    provider_id: str,
    provider_type: ProviderType | str,
    auth_type: AuthType,
    *,
    model: str | None = None,
) -> LibrarianProvider:
    config: dict[str, JSONValue] = {}
    if model is not None:
        config["model"] = model
    return LibrarianProvider(
        id=provider_id,
        name=provider_id,
        provider_type=provider_type,
        auth_type=auth_type,
        enabled=True,
        config=config,
        created_at=datetime(2026, 1, 1, tzinfo=UTC),
        updated_at=datetime(2026, 1, 1, tzinfo=UTC),
    )


def _request(
    prompt: str,
    provider_id: str = "provider-1",
) -> SkillAcquisitionExecutionRequest:
    return SkillAcquisitionExecutionRequest(
        job_id="job-1",
        prompt=prompt,
        agent_name="Hermes",
        project=None,
        task_summary=None,
        provider_id=provider_id,
        librarian_profile_id=None,
    )


def _fake_oauth_jwt(*, account_id: str) -> str:
    header = _base64_url_json({"alg": "none"})
    payload = _base64_url_json(
        {
            "https://api.openai.com/auth": {
                "chatgpt_account_id": account_id,
            },
        }
    )
    return f"{header}.{payload}.signature"


def _base64_url_json(value: dict[str, str | dict[str, str]]) -> str:
    raw = json.dumps(value, separators=(",", ":")).encode()
    return base64.urlsafe_b64encode(raw).decode().rstrip("=")


def test_openai_skill_executor_parses_strict_json_from_openai_response() -> None:
    async def run_case() -> None:
        configs: list[OpenAIClientConfig] = []
        provider = _provider("openai-main", ProviderType.OPENAI, AuthType.API_KEY)
        secret_repo = FakeSecretRepository(
            {("openai-main", ProviderSecretKey.API_KEY.value): "sk-secret-value"}
        )
        responses_payload = json.dumps(
            {
                "title": "Browser automation skill",
                "purpose": "Drive browser interactions deterministically.",
                "content": "Use Playwright with stable selectors.",
                "summary": "Automate stable browser interactions.",
                "tags": ["automation", "browser"],
                "required_tools": ["playwright", "pytest"],
                "evidence_urls": ["https://example.com/skill"],
                "source_summary": "Test evidence summary.",
                "next_steps": ["Wrap into a route test.", "Persist the skill."],
                "risk_level": "LOW",
                "version": "1.1.0",
                "activate": True,
                "status": "ACTIVE",
            },
            separators=(",", ":"),
        )
        fenced = f"```json\n{responses_payload}\n```"
        response_text = fenced
        client = FakeOpenAIClient(response_text)

        def build_client(config: OpenAIClientConfig) -> FakeOpenAIClient:
            configs.append(config)
            return client

        executor = OpenAISkillAcquisitionExecutor(
            provider_repo=cast(
                ILibrarianProviderRepository, FakeProviderRepository([provider])
            ),
            secret_repo=cast(IProviderSecretRepository, secret_repo),
            openai_client_builder=cast(OpenAIClientBuilder, build_client),
        )

        artifact = await executor.acquire_skill(
            _request("Acquire deterministic browser skill.", provider_id="openai-main")
        )

        assert len(configs) == 1
        assert configs[0].api_key == "sk-secret-value"
        assert configs[0].base_url is None
        assert configs[0].default_headers is None
        assert artifact.title == "Browser automation skill"
        assert artifact.purpose == "Drive browser interactions deterministically."
        assert artifact.content == "Use Playwright with stable selectors."
        assert artifact.summary == "Automate stable browser interactions."
        assert artifact.tags == ["automation", "browser"]
        assert artifact.required_tools == ["playwright", "pytest"]
        assert artifact.evidence_urls == ["https://example.com/skill"]
        assert artifact.source_summary == "Test evidence summary."
        assert artifact.next_steps == ["Wrap into a route test.", "Persist the skill."]
        assert artifact.activate is True
        assert artifact.version == "1.1.0"
        assert artifact.status.value == "ACTIVE"
        assert artifact.risk_level.value == "LOW"
        assert client.responses.calls[0]["model"] == "gpt-5.5"
        instructions = str(client.responses.calls[0]["instructions"])
        assert "title, purpose, content" in instructions
        assert "next_steps" in instructions
        assert "status" in instructions
        assert "STRICT JSON" not in repr(artifact)

    anyio.run(run_case)


def test_openai_skill_executor_uses_codex_oauth_and_streaming_response() -> None:
    async def run_case() -> None:
        configs: list[OpenAIClientConfig] = []
        provider = _provider(
            "codex-main",
            ProviderType.OPENAI_CODEX,
            AuthType.OAUTH,
            model="gpt-5.5",
        )
        secret_repo = FakeSecretRepository(
            {
                (
                    "codex-main",
                    ProviderSecretKey.OAUTH_ACCESS_TOKEN.value,
                ): _fake_oauth_jwt(account_id="acct-test-123"),
                (
                    "codex-main",
                    ProviderSecretKey.OAUTH_EXPIRES_AT.value,
                ): (datetime.now(UTC) + timedelta(hours=1)).isoformat(),
            }
        )
        response_text = json.dumps(
            {
                "title": "Codex test skill",
                "purpose": "Use Codex path through OAuth.",
                "content": "Use OpenAI-compatible responses API stream summary.",
                "summary": "Codex generated deterministic response.",
                "tags": ["codex"],
                "required_tools": ["openai-sdk"],
                "evidence_urls": [],
                "source_summary": "OAuth path test.",
                "next_steps": ["No follow-ups."],
                "risk_level": "LOW",
                "version": "1.0.0",
                "activate": False,
                "status": "DRAFT",
            },
            separators=(",", ":"),
        )
        client = FakeOpenAIClient(response_text)

        def build_client(config: OpenAIClientConfig) -> FakeOpenAIClient:
            configs.append(config)
            return client

        executor = OpenAISkillAcquisitionExecutor(
            provider_repo=cast(
                ILibrarianProviderRepository, FakeProviderRepository([provider])
            ),
            secret_repo=cast(IProviderSecretRepository, secret_repo),
            openai_client_builder=cast(OpenAIClientBuilder, build_client),
        )

        artifact = await executor.acquire_skill(
            _request("Use codex path", provider_id="codex-main")
        )

        assert len(configs) == 1
        assert configs[0].base_url == "https://chatgpt.com/backend-api/codex"
        assert configs[0].default_headers == {
            "User-Agent": "codex_cli_rs/0.0.0 (Alexandria Hermes)",
            "originator": "codex_cli_rs",
            "ChatGPT-Account-ID": "acct-test-123",
        }
        call = client.responses.calls[0]
        assert call["input"] == [{"role": "user", "content": "Use codex path"}]
        assert call["store"] is False
        assert call["stream"] is True
        assert artifact.status.value == "DRAFT"

    anyio.run(run_case)


def test_openai_skill_executor_rejects_invalid_json_response_and_keeps_secrets_safe() -> (
    None
):
    async def run_case() -> None:
        provider = _provider("openai-main", ProviderType.OPENAI, AuthType.API_KEY)
        secret_repo = FakeSecretRepository(
            {("openai-main", ProviderSecretKey.API_KEY.value): "sk-secret-value"}
        )
        client = FakeOpenAIClient("This is not JSON")
        executor = OpenAISkillAcquisitionExecutor(
            provider_repo=cast(
                ILibrarianProviderRepository, FakeProviderRepository([provider])
            ),
            secret_repo=cast(IProviderSecretRepository, secret_repo),
        )
        executor.openai_client_builder = lambda _: client

        with pytest.raises(
            LibrarianSkillAcquisitionArtifactError, match="strict JSON"
        ) as exc_info:
            await executor.acquire_skill(
                _request("Invalid JSON test", provider_id="openai-main")
            )
        assert "sk-secret-value" not in str(exc_info.value)

    anyio.run(run_case)


def test_openai_skill_executor_wraps_provider_errors_without_secret_leak(
    caplog: pytest.LogCaptureFixture,
) -> None:
    async def run_case() -> None:
        provider = _provider("openai-main", ProviderType.OPENAI, AuthType.API_KEY)
        secret_repo = FakeSecretRepository(
            {("openai-main", ProviderSecretKey.API_KEY.value): "SECRET-TOKEN"}
        )
        executor = OpenAISkillAcquisitionExecutor(
            provider_repo=cast(
                ILibrarianProviderRepository, FakeProviderRepository([provider])
            ),
            secret_repo=cast(IProviderSecretRepository, secret_repo),
        )
        executor.openai_client_builder = lambda _: FailingOpenAIClient()

        with pytest.raises(
            LibrarianSkillAcquisitionExecutionError,
            match="Skill acquisition execution failed",
        ) as exc_info:
            await executor.acquire_skill(
                _request("Provider error test", provider_id="openai-main")
            )

        assert "SECRET-TOKEN" not in str(exc_info.value)
        assert "SECRET-TOKEN" not in caplog.text

    anyio.run(run_case)


def test_openai_skill_executor_rejects_unsupported_provider_type() -> None:
    async def run_case() -> None:
        provider = _provider("legacy-storage", "LEGACY_STORAGE", AuthType.NONE)
        secret_repo = FakeSecretRepository({})
        executor = OpenAISkillAcquisitionExecutor(
            provider_repo=cast(
                ILibrarianProviderRepository, FakeProviderRepository([provider])
            ),
            secret_repo=cast(IProviderSecretRepository, secret_repo),
        )

        with pytest.raises(LibrarianSkillAcquisitionProviderError, match="unsupported"):
            await executor.acquire_skill(
                _request(
                    "Unsupported provider type test",
                    provider_id="legacy-storage",
                )
            )

    anyio.run(run_case)
