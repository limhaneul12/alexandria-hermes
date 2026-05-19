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
from app.library.application.item_service import ItemService
from app.library.application.skill_service import SkillService
from app.library.domain.contracts.item_contracts import ItemCreate, ItemUpdate
from app.library.domain.entities.item_search_hit import ItemSearchCandidate
from app.library.domain.entities.item_search_query import ItemSearchQuery
from app.library.domain.entities.read_models import LibraryItem
from app.library.domain.event_enum.item_enums import ItemType
from app.library.domain.repositories.item_repository import IItemRepository
from app.memory.application.context_service import ContextService
from app.memory.domain.entities.context_read_models import ContextRecord
from app.memory.domain.event_enum.context_enums import (
    ContextContentFormat,
    ContextImportance,
    ContextKind,
    ContextScope,
    ContextSourceType,
    ContextStorageStatus,
)
from app.memory.infrastructure.repositories.context_repository import (
    SqlAlchemyContextRepository,
)
from app.shared.exceptions import ValidationError
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


class FakeItemRepository(IItemRepository):
    """In-memory item repository used by the real skill service."""

    def __init__(self) -> None:
        """Initialize captured item state."""
        self.created: LibraryItem | None = None
        self.create_count = 0

    async def create(self, *, payload: ItemCreate) -> LibraryItem:
        """Create one in-memory skill item."""
        self.create_count += 1
        self.created = LibraryItem(
            id="00000000-0000-4000-8000-000000000777",
            item_type=payload.item_type.value,
            title=payload.title,
            summary=payload.summary,
            content=payload.content,
            category_id=payload.category_id,
            tags=payload.tags,
            status=payload.status.value,
            source_type=payload.source_type.value,
            created_by_type=payload.created_by_type,
            created_by_name=payload.created_by_name,
            details=payload.details,
            created_at=_NOW,
            updated_at=_NOW,
            is_archived=False,
        )
        return self.created

    async def update(
        self,
        item_id: str,
        *,
        payload: ItemUpdate,
    ) -> LibraryItem:
        """Update is unused by these tests."""
        raise AssertionError("update should not be called")

    async def get(self, item_id: str) -> LibraryItem | None:
        """Get is unused by these tests."""
        return None

    async def delete(self, item_id: str) -> None:
        """Delete is unused by these tests."""

    async def list_by_type(
        self,
        *,
        item_type: ItemType,
        limit: int | None = None,
        offset: int = 0,
    ) -> list[LibraryItem]:
        """List is unused by these tests."""
        return []

    async def list_all(
        self,
        *,
        limit: int | None = None,
        offset: int = 0,
        category_id: str | None = None,
        search_query: str | None = None,
    ) -> tuple[list[LibraryItem], int]:
        """List all is unused by these tests."""
        return [], 0

    async def search(
        self, query: str, item_type: ItemType | None = None
    ) -> list[LibraryItem]:
        """Search is unused by these tests."""
        return []

    async def search_candidates(
        self,
        options: ItemSearchQuery,
    ) -> tuple[list[ItemSearchCandidate], int]:
        """Candidate search is unused by these tests."""
        return [], 0


class FakeContextService:
    """Context service fake that records resume compact packets."""

    def __init__(self) -> None:
        """Initialize captured compact state."""
        self.compact: dict[str, object] | None = None

    async def prepare_compact(
        self,
        current_goal: str,
        completed: list[str],
        in_progress: list[str],
        key_decisions: list[str],
        next_actions: list[str],
        risks: list[str],
        project: str | None = None,
        scope: ContextScope = ContextScope.PROJECT,
        workspace_id: str | None = None,
        agent_id: str | None = None,
        user_id: str | None = None,
        session_id: str | None = None,
        visibility: ContextScope = ContextScope.PROJECT,
        source_agent: str = "Hermes",
    ) -> ContextRecord:
        """Capture the compact packet and return a persisted context handle."""
        self.compact = {
            "current_goal": current_goal,
            "completed": completed,
            "in_progress": in_progress,
            "key_decisions": key_decisions,
            "next_actions": next_actions,
            "risks": risks,
            "project": project,
            "source_agent": source_agent,
        }
        return ContextRecord(
            id="00000000-0000-4000-8000-000000000888",
            kind=ContextKind.COMPACT,
            title=current_goal,
            summary="Resume packet.",
            content="\n".join([current_goal, *completed, *next_actions]),
            content_format=ContextContentFormat.MARKDOWN,
            project=project,
            scope=scope,
            workspace_id=workspace_id,
            agent_id=agent_id,
            user_id=user_id,
            session_id=session_id,
            visibility=visibility,
            source_agent=source_agent,
            source_type=ContextSourceType.AGENT,
            importance=ContextImportance.HIGH,
            tags=["compact", "handoff"],
            status=ContextStorageStatus.SAVED,
            quality_score=100,
            warnings=[],
            restore_prompt="Continue from this compact context.",
            context_metadata={},
            created_at=_NOW,
            updated_at=_NOW,
            last_accessed_at=None,
            expires_at=None,
            archived_at=None,
            access_count=0,
            is_archived=False,
        )


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
    skill_service: SkillService | None = None,
    context_service: object | None = None,
) -> tuple[Database, AsyncSession, SkillAcquisitionService]:
    database = Database(database_url=f"sqlite+aiosqlite:///{path}", create_schema=True)
    await database.initialize()
    session = database.session()
    if skill_service is None:
        skill_service = SkillService(item_service=ItemService(FakeItemRepository()))
    if context_service is None:
        context_service = FakeContextService()
    service = SkillAcquisitionService(
        repository=SqlAlchemySkillAcquisitionJobRepository(session=session),
        provider_repo=FakeProviderRepository(providers),
        secret_repo=FakeSecretRepository(secrets),
        skill_service=skill_service,
        context_service=context_service,  # type: ignore[arg-type]
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
    """Failed jobs should not create a skill or resume packet on completion."""

    async def run_case() -> tuple[str, int, object | None]:
        item_repo = FakeItemRepository()
        context_service = FakeContextService()
        database, session, service = await _service(
            tmp_path / "failed-complete.db",
            providers=[_provider()],
            secrets={},
            skill_service=SkillService(item_service=ItemService(item_repo=item_repo)),
            context_service=context_service,
        )
        try:
            job = await service.request_job(
                prompt="Need a deterministic HTTP mocking skill",
                provider_id="provider-1",
                agent_name="Hermes",
            )
            with pytest.raises(
                ValidationError, match="Skill acquisition job is not completable"
            ) as exc_info:
                await service.complete_with_skill_artifact(
                    job_id=job.id,
                    artifact=SkillAcquisitionArtifact(
                        title="HTTP boundary fake skill",
                        purpose="Build deterministic API boundary fakes.",
                        content="Prefer boundary fakes over internal mocks.",
                    ),
                )
            return str(exc_info.value), item_repo.create_count, context_service.compact
        finally:
            await _close(database, session)

    error_message, create_count, compact = anyio.run(run_case)

    assert error_message == "Skill acquisition job is not completable"
    assert create_count == 0
    assert compact is None


def test_skill_acquisition_completion_persists_skill_and_resume_packet(
    tmp_path: Path,
) -> None:
    """Completing a guidance-only job should persist a skill and resume context."""

    async def run_case() -> tuple[
        SkillAcquisitionJobStatus,
        bool,
        str | None,
        str | None,
        LibraryItem,
        dict[str, object],
    ]:
        item_repo = FakeItemRepository()
        context_service = FakeContextService()
        database, session, service = await _service(
            tmp_path / "complete.db",
            providers=[],
            secrets={},
            skill_service=SkillService(item_service=ItemService(item_repo=item_repo)),
            context_service=context_service,
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
            assert item_repo.created is not None
            assert context_service.compact is not None
            return (
                completed.status,
                completed.result_available,
                completed.skill_id,
                completed.context_id,
                item_repo.created,
                context_service.compact,
            )
        finally:
            await _close(database, session)

    (
        status,
        result_available,
        skill_id,
        context_id,
        created,
        compact,
    ) = anyio.run(run_case)

    assert status is SkillAcquisitionJobStatus.COMPLETED
    assert result_available is True
    assert skill_id == "00000000-0000-4000-8000-000000000777"
    assert context_id == "00000000-0000-4000-8000-000000000888"
    assert created.source_type == "AGENT_SUBMITTED"
    assert created.created_by_name == "Hermes"
    assert created.tags == ["http", "skill-acquisition", "testing"]
    assert created.details["evidence_urls"] == ["https://example.com/http-fake"]
    assert created.details["acquisition_method"] == "SELF_ACQUISITION"
    assert compact["project"] == "alexandria-hermes"
    assert "Apply the skill" in compact["next_actions"][0]


def test_skill_acquisition_completion_context_pack_contains_required_headings(
    tmp_path: Path,
) -> None:
    """Resume packets created during completion must include the required headings."""

    async def run_case() -> tuple[str | None, str]:
        database = Database(
            database_url=f"sqlite+aiosqlite:///{tmp_path / 'complete-compact.db'}",
            create_schema=True,
        )
        await database.initialize()
        session = database.session()
        try:
            context_service = ContextService(
                repository=SqlAlchemyContextRepository(session=session),
            )
            item_repo = FakeItemRepository()
            service = SkillAcquisitionService(
                repository=SqlAlchemySkillAcquisitionJobRepository(session=session),
                provider_repo=FakeProviderRepository(providers=[]),
                secret_repo=FakeSecretRepository(secrets={}),
                skill_service=SkillService(
                    item_service=ItemService(item_repo=item_repo)
                ),
                context_service=context_service,
                now_provider=lambda: _NOW,
            )

            job = await service.request_job(
                prompt="Need a robust HTTP mock skill",
                agent_name="Hermes",
                project="alexandria-hermes",
                task_summary="Keep brittle tests deterministic.",
            )
            completed = await service.complete_with_skill_artifact(
                job_id=job.id,
                artifact=SkillAcquisitionArtifact(
                    title="HTTP mock skill",
                    purpose="Stabilize third-party API tests.",
                    summary="Use explicit context handoff for resume.",
                    content="Prefer mock-based external boundaries.",
                    tags=["testing", "mocks"],
                    required_tools=["pytest"],
                    evidence_urls=["https://example.com/http-mock"],
                    source_summary="Hermes prepared a handoff-friendly packet.",
                    next_steps=["Resume the verification task."],
                ),
            )

            resume_context = await context_service.get(completed.context_id)
            assert resume_context is not None
            assert completed.skill_id == "00000000-0000-4000-8000-000000000777"
            assert completed.context_id is not None
            assert completed.context_id == resume_context.id
            return resume_context.content, completed.skill_id
        finally:
            await session.commit()
            await session.close()
            await database.shutdown()

    content, skill_id = anyio.run(run_case)

    assert skill_id == "00000000-0000-4000-8000-000000000777"
    assert "## Summary" in content
    assert "## Summary\nCompact handoff prepared for Alexandria-Hermes." in content
    assert "## Restore Prompt" in content
    assert (
        "## Restore Prompt\nContinue from this Alexandria-Hermes compact context."
        in content
    )
