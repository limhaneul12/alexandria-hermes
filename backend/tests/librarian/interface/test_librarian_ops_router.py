"""Librarian durable operation router contract tests."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime

from app.librarian.domain.entities.skill_acquisition_job import SkillAcquisitionJob
from app.librarian.domain.event_enum.collaboration_enums import (
    SkillAcquisitionJobStatus,
)
from app.main import app
from dependency_injector import providers
from fastapi.testclient import TestClient
from tests.shared.provider_overrides import override_library_provider


@contextmanager
def _override_librarian_provider(
    provider_name: str,
    value: object,
) -> Iterator[None]:
    """Temporarily override one librarian container provider."""
    provider = app.state.container.librarian.providers[provider_name]
    with provider.override(providers.Object(value)):
        yield


class FakeSkillAcquisitionService:
    """Deterministic durable acquisition job service for router tests."""

    def __init__(
        self,
        *,
        status: SkillAcquisitionJobStatus = SkillAcquisitionJobStatus.ACCEPTED,
        result_summary: str = "Skill acquisition job accepted.",
    ) -> None:
        """Initialize captured job state."""
        self.status = status
        self.result_summary = result_summary
        self.job = SkillAcquisitionJob(
            id="skill-acquisition-1",
            prompt="Need a browser automation skill",
            agent_name="Hermes",
            project="alexandria-hermes",
            task_summary="Investigate Playwright usage.",
            status=self.status,
            provider_id="00000000-0000-4000-8000-000000000501",
            librarian_profile_id=None,
            skill_id=None,
            context_id=None,
            result_summary=self.result_summary,
            evidence_urls=[],
            error_message=None,
            created_at=datetime(2026, 5, 18, 17, 30, tzinfo=UTC),
            updated_at=datetime(2026, 5, 18, 17, 30, tzinfo=UTC),
            completed_at=None,
        )

    async def request_job(
        self,
        *,
        prompt: str,
        agent_name: str = "Hermes",
        project: str | None = None,
        task_summary: str | None = None,
        provider_id: str | None = None,
        librarian_profile_id: str | None = None,
    ) -> SkillAcquisitionJob:
        """Return one accepted durable job."""
        self.job = SkillAcquisitionJob(
            id="skill-acquisition-1",
            prompt=prompt,
            agent_name=agent_name,
            project=project,
            task_summary=task_summary,
            status=self.status,
            provider_id=provider_id,
            librarian_profile_id=librarian_profile_id,
            skill_id=None,
            context_id=None,
            result_summary=self.result_summary,
            evidence_urls=[],
            error_message=None,
            created_at=datetime(2026, 5, 18, 17, 30, tzinfo=UTC),
            updated_at=datetime(2026, 5, 18, 17, 30, tzinfo=UTC),
            completed_at=None,
        )
        return self.job

    async def get_job(self, job_id: str) -> SkillAcquisitionJob:
        """Return the captured job."""
        _ = job_id
        return self.job

    async def complete_with_skill_artifact(self, job_id, artifact):  # type: ignore[no-untyped-def]
        """Return a completed job with sanitized skill and context handles."""
        _ = job_id
        self.job = SkillAcquisitionJob(
            id=self.job.id,
            prompt=self.job.prompt,
            agent_name=self.job.agent_name,
            project=self.job.project,
            task_summary=self.job.task_summary,
            status=SkillAcquisitionJobStatus.COMPLETED,
            provider_id=self.job.provider_id,
            librarian_profile_id=self.job.librarian_profile_id,
            skill_id="00000000-0000-4000-8000-000000000777",
            context_id="00000000-0000-4000-8000-000000000888",
            result_summary=f"Persisted {artifact.title}.",
            evidence_urls=list(artifact.evidence_urls),
            error_message=None,
            created_at=self.job.created_at,
            updated_at=datetime(2026, 5, 18, 17, 31, tzinfo=UTC),
            completed_at=datetime(2026, 5, 18, 17, 31, tzinfo=UTC),
        )
        return self.job


class FakeSkillAcquisitionRunner:
    """Minimal non-network background runner for scheduling checks."""

    def __init__(self) -> None:
        """Initialize runner call history."""
        self.run_job_calls: list[str] = []

    async def run_job(self, job_id: str) -> None:
        """Record one scheduled background run."""
        self.run_job_calls.append(job_id)


def test_skill_acquisition_job_routes_return_sanitized_durable_status() -> None:
    """Skill acquisition routes should create and poll durable sanitized jobs."""
    service = FakeSkillAcquisitionService()
    runner = FakeSkillAcquisitionRunner()

    with (
        override_library_provider("skill_acquisition_service", service),
        _override_librarian_provider("skill_acquisition_runner", runner),
        TestClient(app, raise_server_exceptions=False) as client,
    ):
        create_response = client.post(
            "/librarians/skill-acquisition-jobs",
            json={
                "prompt": "Need a browser automation skill",
                "agent_name": "Hermes",
                "project": "alexandria-hermes",
                "task_summary": "Investigate Playwright usage.",
                "provider_id": "00000000-0000-4000-8000-000000000501",
            },
        )
        status_response = client.get(
            "/librarians/skill-acquisition-jobs/skill-acquisition-1"
        )

    assert create_response.status_code == 202
    assert status_response.status_code == 200
    body = create_response.json()
    serialized = f"{body}{status_response.json()}"
    assert body["id"] == "skill-acquisition-1"
    assert body["status"] == "ACCEPTED"
    assert body["result_available"] is False
    assert body["prompt"] == "Need a browser automation skill"
    assert "SECRET" not in serialized
    assert "api_key" not in serialized
    assert runner.run_job_calls == ["skill-acquisition-1"]


def test_skill_acquisition_job_does_not_schedule_background_runner_for_non_accepted() -> (
    None
):
    """GUIDANCE_ONLY and FAILED jobs should never schedule a background run."""
    for status in (
        SkillAcquisitionJobStatus.GUIDANCE_ONLY,
        SkillAcquisitionJobStatus.FAILED,
    ):
        service = FakeSkillAcquisitionService(
            status=status,
            result_summary="Non-accepted skill-acquisition job.",
        )
        runner = FakeSkillAcquisitionRunner()

        with (
            override_library_provider("skill_acquisition_service", service),
            _override_librarian_provider("skill_acquisition_runner", runner),
            TestClient(app, raise_server_exceptions=False) as client,
        ):
            create_response = client.post(
                "/librarians/skill-acquisition-jobs",
                json={
                    "prompt": "Need a browser automation skill",
                    "agent_name": "Hermes",
                    "project": "alexandria-hermes",
                    "task_summary": "Investigate Playwright usage.",
                    "provider_id": "00000000-0000-4000-8000-000000000501",
                },
            )

        assert create_response.status_code == 202
        assert create_response.json()["status"] == status.value
        assert runner.run_job_calls == []


def test_skill_acquisition_completion_route_returns_resume_handles() -> None:
    """Completion route should return persisted skill and context handles."""
    service = FakeSkillAcquisitionService()

    with (
        override_library_provider("skill_acquisition_service", service),
        TestClient(app, raise_server_exceptions=False) as client,
    ):
        response = client.post(
            "/librarians/skill-acquisition-jobs/skill-acquisition-1/complete",
            json={
                "title": "Browser automation skill",
                "purpose": "Use browser automation deterministically.",
                "content": "Use a real browser boundary and stable selectors.",
                "summary": "Skill persisted from async acquisition.",
                "tags": ["browser"],
                "evidence_urls": ["https://example.com/browser"],
                "source_summary": "Provider returned a sanitized artifact.",
                "next_steps": ["Apply this skill to the waiting browser task."],
            },
        )

    assert response.status_code == 200
    body = response.json()
    assert {
        "status": body["status"],
        "result_available": body["result_available"],
        "skill_id": body["skill_id"],
        "context_id": body["context_id"],
        "evidence_urls": body["evidence_urls"],
    } == {
        "status": "COMPLETED",
        "result_available": True,
        "skill_id": "00000000-0000-4000-8000-000000000777",
        "context_id": "00000000-0000-4000-8000-000000000888",
        "evidence_urls": ["https://example.com/browser"],
    }


def test_skill_acquisition_status_route_returns_resume_handles_after_completion() -> (
    None
):
    """Polling the status route after completion should expose durable result handles."""
    service = FakeSkillAcquisitionService()

    with (
        override_library_provider("skill_acquisition_service", service),
        TestClient(app, raise_server_exceptions=False) as client,
    ):
        create_response = client.post(
            "/librarians/skill-acquisition-jobs",
            json={"prompt": "Need a browser automation skill"},
        )
        complete_response = client.post(
            "/librarians/skill-acquisition-jobs/skill-acquisition-1/complete",
            json={
                "title": "Browser automation skill",
                "purpose": "Use browser automation deterministically.",
                "content": "Use a real browser boundary and stable selectors.",
                "summary": "Skill persisted from async acquisition.",
            },
        )
        status_response = client.get(
            "/librarians/skill-acquisition-jobs/skill-acquisition-1"
        )

    assert create_response.status_code == 202
    assert complete_response.status_code == 200
    assert status_response.status_code == 200
    assert status_response.json()["status"] == "COMPLETED"
    assert status_response.json()["result_available"] is True
    assert status_response.json()["skill_id"] == "00000000-0000-4000-8000-000000000777"
    assert (
        status_response.json()["context_id"] == "00000000-0000-4000-8000-000000000888"
    )
    assert "SECRET" not in status_response.text
