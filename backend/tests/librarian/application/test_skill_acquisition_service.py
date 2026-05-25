"""Durable skill-acquisition service behavior tests."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import anyio
import pytest
from app.connections.domain.entities.read_models import LibrarianProvider
from app.connections.domain.event_enum.provider_enums import AuthType, ProviderType
from app.connections.domain.repositories.librarian_repository import (
    ILibrarianProviderRepository,
    IProviderSecretRepository,
)
from app.librarian.application.skill_acquisition_service import (
    SkillAcquisitionService,
)
from app.librarian.domain.contracts.skill_acquisition_contracts import (
    SkillAcquisitionArtifact,
)
from app.librarian.domain.event_enum.collaboration_enums import (
    SkillAcquisitionJobStatus,
)
from app.librarian.infrastructure.repositories.skill_acquisition_job_repository import (
    SqlAlchemySkillAcquisitionJobRepository,
)
from app.shared.exceptions import LibrarianValidationError
from app.shared.infrastructure.database import Database
from sqlalchemy.ext.asyncio import AsyncSession

_NOW = datetime(2026, 5, 18, 17, 30, tzinfo=UTC)


class FakeProviderRepository(ILibrarianProviderRepository):
    """Provider repository fake for skill-acquisition service tests."""

    def __init__(self, providers: list[LibrarianProvider]) -> None:
        """Initialize fake providers."""
        self._providers = providers

    async def create(self, payload):  # type: ignore[no-untyped-def]
        """Unused in these tests."""
        raise NotImplementedError

    async def get(self, provider_id: str) -> LibrarianProvider | None:
        """Return one provider by id."""
        return next(
            (provider for provider in self._providers if provider.id == provider_id),
            None,
        )

    async def list_all(self) -> list[LibrarianProvider]:
        """Return all configured providers."""
        return list(self._providers)

    async def update(self, provider_id, payload):  # type: ignore[no-untyped-def]
        """Unused in these tests."""
        raise NotImplementedError

    async def delete(self, provider_id: str) -> None:
        """Unused in these tests."""
        raise NotImplementedError


class FakeSecretRepository(IProviderSecretRepository):
    """Provider secret fake that never exposes secrets in job payloads."""

    def __init__(self, secrets: dict[tuple[str, str], str]) -> None:
        """Initialize fake secrets."""
        self._secrets = secrets

    async def resolve(self, provider_id: str, key_name: str) -> str | None:
        """Resolve one fake secret."""
        return self._secrets.get((provider_id, key_name))

    async def set_secret(self, *, provider_id: str, key_name: str, value: str) -> None:
        """Unused in these tests."""
        raise NotImplementedError

    async def delete_for_provider(self, provider_id: str, key_name: str) -> None:
        """Unused in these tests."""
        raise NotImplementedError


def _provider(provider_id: str = "provider-1") -> LibrarianProvider:
    return LibrarianProvider(
        id=provider_id,
        name="OpenAI",
        provider_type=ProviderType.OPENAI,
        auth_type=AuthType.API_KEY,
        enabled=True,
        config={},
        created_at=_NOW,
        updated_at=_NOW,
    )


async def _service(
    path: Path,
    *,
    providers: list[LibrarianProvider],
    secrets: dict[tuple[str, str], str],
) -> tuple[Database, AsyncSession, SkillAcquisitionService]:
    database = Database(database_url=f"sqlite+aiosqlite:///{path}", create_schema=True)
    await database.initialize()
    session = database.session()
    service = SkillAcquisitionService(
        repository=SqlAlchemySkillAcquisitionJobRepository(session=session),
        provider_repo=FakeProviderRepository(providers),
        secret_repo=FakeSecretRepository(secrets),
        now_provider=lambda: _NOW,
    )
    return database, session, service


async def _close(database: Database, session: AsyncSession) -> None:
    await session.commit()
    await session.close()
    await database.shutdown()


def test_skill_acquisition_job_returns_guidance_when_no_provider_exists(
    tmp_path: Path,
) -> None:
    """Missing providers should create a durable guidance-only job."""

    async def run_case() -> tuple[SkillAcquisitionJobStatus, bool, str | None]:
        database, session, service = await _service(
            tmp_path / "guidance.db", providers=[], secrets={}
        )
        try:
            job = await service.request_job(
                prompt="Need a Playwright skill",
                agent_name="Hermes",
                project="alexandria-hermes",
                task_summary="Browser automation gap",
            )
            persisted = await service.get_job(job.id)
            return persisted.status, persisted.result_available, persisted.error_message
        finally:
            await _close(database, session)

    status, result_available, error_message = anyio.run(run_case)

    assert status is SkillAcquisitionJobStatus.GUIDANCE_ONLY
    assert result_available is False
    assert error_message is None


def test_skill_acquisition_job_is_accepted_when_provider_can_execute(
    tmp_path: Path,
) -> None:
    """Executable providers should create a durable accepted job without secrets."""

    async def run_case() -> tuple[SkillAcquisitionJobStatus, str | None, str]:
        database, session, service = await _service(
            tmp_path / "accepted.db",
            providers=[_provider()],
            secrets={("provider-1", "api_key"): "SECRET-KEY"},
        )
        try:
            job = await service.request_job(
                prompt="Need a FastAPI skill",
                provider_id="provider-1",
                agent_name="Hermes",
            )
            serialized = f"{job}"
            return job.status, job.provider_id, serialized
        finally:
            await _close(database, session)

    status, provider_id, serialized = anyio.run(run_case)

    assert status is SkillAcquisitionJobStatus.ACCEPTED
    assert provider_id == "provider-1"
    assert "SECRET-KEY" not in serialized


def test_skill_acquisition_job_fails_without_provider_credentials(
    tmp_path: Path,
) -> None:
    """A selected provider without credentials should persist a sanitized failure."""

    async def run_case() -> tuple[SkillAcquisitionJobStatus, str | None]:
        database, session, service = await _service(
            tmp_path / "failed.db", providers=[_provider()], secrets={}
        )
        try:
            job = await service.request_job(
                prompt="Need a FastAPI skill",
                provider_id="provider-1",
                agent_name="Hermes",
            )
            return job.status, job.error_message
        finally:
            await _close(database, session)

    status, error_message = anyio.run(run_case)

    assert status is SkillAcquisitionJobStatus.FAILED
    assert error_message == "Provider credentials unavailable"


def test_skill_acquisition_completion_rejects_failed_jobs(
    tmp_path: Path,
) -> None:
    """Failed jobs should not create a resume packet on completion."""

    async def run_case() -> str:
        database, session, service = await _service(
            tmp_path / "failed-complete.db",
            providers=[_provider()],
            secrets={},
        )
        try:
            job = await service.request_job(
                prompt="Need a deterministic HTTP mocking skill",
                provider_id="provider-1",
                agent_name="Hermes",
            )
            with pytest.raises(
                LibrarianValidationError,
                match="Skill acquisition job is not completable",
            ) as exc_info:
                await service.complete_with_skill_artifact(
                    job_id=job.id,
                    artifact=SkillAcquisitionArtifact(
                        title="HTTP boundary fake skill",
                        purpose="Build deterministic API boundary fakes.",
                        content="Prefer boundary fakes over internal mocks.",
                    ),
                )
            return str(exc_info.value)
        finally:
            await _close(database, session)

    error_message = anyio.run(run_case)

    assert error_message == "Skill acquisition job is not completable"


def test_skill_acquisition_completion_records_artifact_without_context_write(
    tmp_path: Path,
) -> None:
    """Completing a guidance-only job should skip SQLite skill and context CRUD."""

    async def run_case() -> tuple[
        SkillAcquisitionJobStatus,
        bool,
        str | None,
        str | None,
        list[str],
    ]:
        database, session, service = await _service(
            tmp_path / "complete.db",
            providers=[],
            secrets={},
        )
        try:
            job = await service.request_job(
                prompt="Need a deterministic HTTP mocking skill",
                agent_name="Hermes",
                project="alexandria-hermes",
                task_summary="Replace brittle API tests.",
            )
            completed = await service.complete_with_skill_artifact(
                job_id=job.id,
                artifact=SkillAcquisitionArtifact(
                    title="HTTP boundary fake skill",
                    purpose="Build deterministic API boundary fakes.",
                    summary="Use fake HTTP boundaries instead of internals.",
                    content="Prefer boundary fakes over internal collaborator mocks.",
                    tags=["testing", "http"],
                    required_tools=["pytest"],
                    evidence_urls=[" https://example.com/http-fake "],
                    source_summary="Hermes researched the missing capability.",
                    next_steps=["Apply the skill to the failing route test."],
                ),
            )
            return (
                completed.status,
                completed.result_available,
                completed.skill_id,
                completed.context_id,
                completed.evidence_urls,
            )
        finally:
            await _close(database, session)

    status, result_available, skill_id, context_id, evidence_urls = anyio.run(run_case)

    assert status is SkillAcquisitionJobStatus.COMPLETED
    assert result_available is True
    assert skill_id is None
    assert context_id is None
    assert evidence_urls == ["https://example.com/http-fake"]
