"""Obsidian librarian workflow checkpoint behavior tests."""

from __future__ import annotations

from pathlib import Path

import anyio
import pytest
from app.obsidian.application.obsidian_librarian_workflow_service import (
    ObsidianLibrarianWorkflowService,
)
from app.obsidian.application.obsidian_service import ObsidianService
from app.obsidian.domain.contracts.obsidian_contracts import (
    ObsidianLibrarianAsk,
    ObsidianLibrarianWorkflowResume,
    ObsidianSaveNote,
)
from app.obsidian.domain.event_enum.obsidian_enums import (
    AlexandriaNoteType,
    ObsidianLibrarianWorkflowStatus,
)
from app.obsidian.infrastructure.models import (
    obsidian_index_models as _obsidian_index_models,
)
from app.obsidian.infrastructure.repositories.obsidian_index_repository import (
    SqlAlchemyObsidianIndexRepository,
)
from app.obsidian.infrastructure.repositories.obsidian_workflow_repository import (
    SqlAlchemyObsidianWorkflowRepository,
)
from app.shared.exceptions import ObsidianValidationError
from app.shared.infrastructure.database import Database
from sqlalchemy.ext.asyncio import AsyncSession

_OBSIDIAN_MODELS_LOADED = _obsidian_index_models


def _database_url(path: Path) -> str:
    return f"sqlite+aiosqlite:///{path}"


async def _services(
    tmp_path: Path,
) -> tuple[Database, AsyncSession, ObsidianService, ObsidianLibrarianWorkflowService]:
    database = Database(
        database_url=_database_url(tmp_path / "obsidian.db"), create_schema=True
    )
    await database.initialize()
    session = database.session()
    obsidian = ObsidianService(
        repository=SqlAlchemyObsidianIndexRepository(session=session),
        vault_path=str(tmp_path / "vault"),
        alexandria_root="Alexandria",
    )
    workflow = ObsidianLibrarianWorkflowService(
        workflow_repository=SqlAlchemyObsidianWorkflowRepository(session=session),
        obsidian_service=obsidian,
    )
    return database, session, obsidian, workflow


def test_librarian_workflow_pauses_then_resumes_approved_writes(
    tmp_path: Path,
) -> None:
    """Workflow should checkpoint pending actions and write only approved notes."""

    async def scenario() -> tuple[str, list[str], str | None, bool]:
        database, session, obsidian, workflow_service = await _services(tmp_path)
        try:
            await obsidian.save_note(
                ObsidianSaveNote(
                    title="Storage Source",
                    body="# Storage Source\n\nObsidian is canonical storage.",
                    alexandria_type=AlexandriaNoteType.CONTEXT,
                    note_id="ctx_storage_source",
                    project="alexandria-hermes",
                )
            )
            workflow = await workflow_service.start_workflow(
                ObsidianLibrarianAsk(
                    query="canonical storage",
                    project="alexandria-hermes",
                    delegate_to_librarian=True,
                    provider_id="codex-oauth",
                    profile_id="research-critic",
                )
            )
            before_related = await obsidian.search(
                query=workflow_query(), refresh=False
            )
            resumed = await workflow_service.resume_workflow(
                ObsidianLibrarianWorkflowResume(
                    thread_id=workflow.thread_id,
                    approved_actions=["save_transcript", "create_context_note"],
                )
            )
            transcript_path = resumed.state.get("transcript_path")
            transcript_exists = (
                isinstance(transcript_path, str)
                and (tmp_path / "vault" / transcript_path).exists()
            )
        finally:
            await session.close()
            await database.shutdown()
        return (
            resumed.status.value,
            list(resumed.state["completed_actions"]),
            transcript_path if isinstance(transcript_path, str) else None,
            len(before_related) == 1 and transcript_exists,
        )

    status, completed_actions, transcript_path, source_found = anyio.run(scenario)

    assert status == ObsidianLibrarianWorkflowStatus.COMPLETED.value
    assert completed_actions[0] == "save_transcript"
    assert completed_actions[1].startswith("create_context_note:")
    assert transcript_path is not None
    assert source_found is True


def test_librarian_workflow_records_oauth_delegate_approval(tmp_path: Path) -> None:
    """Approving OAuth delegation should record the current transparent status."""

    async def scenario() -> list[str]:
        database, session, _obsidian, workflow_service = await _services(tmp_path)
        try:
            workflow = await workflow_service.start_workflow(
                ObsidianLibrarianAsk(
                    query="delegate check",
                    delegate_to_librarian=True,
                    provider_id="codex-oauth",
                    profile_id="research-critic",
                )
            )
            resumed = await workflow_service.resume_workflow(
                ObsidianLibrarianWorkflowResume(
                    thread_id=workflow.thread_id,
                    approved_actions=["ask_oauth_librarian"],
                )
            )
        finally:
            await session.close()
            await database.shutdown()
        return list(resumed.state["completed_actions"])

    assert anyio.run(scenario) == ["ask_oauth_librarian:requested_local_fallback"]


def test_librarian_workflow_rejects_unknown_or_repeated_resume(
    tmp_path: Path,
) -> None:
    """Workflow resume should only accept pending actions once."""

    async def scenario() -> tuple[str, str]:
        database, session, _obsidian, workflow_service = await _services(tmp_path)
        try:
            workflow = await workflow_service.start_workflow(
                ObsidianLibrarianAsk(query="approval check")
            )
            with pytest.raises(ObsidianValidationError) as unknown_error:
                await workflow_service.resume_workflow(
                    ObsidianLibrarianWorkflowResume(
                        thread_id=workflow.thread_id,
                        approved_actions=["not_a_pending_action"],
                    )
                )
            await workflow_service.resume_workflow(
                ObsidianLibrarianWorkflowResume(thread_id=workflow.thread_id)
            )
            with pytest.raises(ObsidianValidationError) as repeated_error:
                await workflow_service.resume_workflow(
                    ObsidianLibrarianWorkflowResume(thread_id=workflow.thread_id)
                )
        finally:
            await session.close()
            await database.shutdown()
        return str(unknown_error.value), str(repeated_error.value)

    unknown_message, repeated_message = anyio.run(scenario)

    assert "unknown workflow action" in unknown_message
    assert repeated_message == "workflow is not waiting for approval"


def workflow_query():
    from app.obsidian.domain.contracts.obsidian_contracts import ObsidianSearchQuery

    return ObsidianSearchQuery(query="canonical storage", limit=3)
