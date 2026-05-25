"""Durable async skill-acquisition job service."""

from __future__ import annotations

import hashlib
from collections.abc import Callable
from datetime import datetime

from app.connections.domain.entities.read_models import LibrarianProvider
from app.connections.domain.repositories.librarian_repository import (
    ILibrarianProviderRepository,
    IProviderSecretRepository,
)
from app.librarian.application.provider_execution_policy import provider_can_execute
from app.librarian.domain.contracts.skill_acquisition_contracts import (
    SkillAcquisitionArtifact,
    SkillAcquisitionJobCreate,
    SkillAcquisitionJobUpdate,
)
from app.librarian.domain.entities.skill_acquisition_job import SkillAcquisitionJob
from app.librarian.domain.event_enum.collaboration_enums import (
    SkillAcquisitionJobStatus,
)
from app.librarian.domain.repositories.skill_acquisition_job_repository import (
    ISkillAcquisitionJobRepository,
)
from app.shared.exceptions import (
    LibrarianResourceNotFoundError,
    LibrarianValidationError,
)
from app.shared.types.types_convert_utils import now_utc
from app.shared.utils.logging import redact_sensitive_text

_JOB_PREFIX = "skill-acquisition-"
_GUIDANCE_SUMMARY = (
    "No executable librarian provider is available. Hermes should research the "
    "missing capability and submit a skill candidate through the agent path."
)
_ACCEPTED_SUMMARY = (
    "Skill acquisition job accepted. Poll this job for a sanitized result packet."
)
_CREDENTIAL_FAILURE = "Provider credentials unavailable"


class SkillAcquisitionService:
    """Create and inspect durable skill-acquisition jobs."""

    def __init__(
        self,
        *,
        repository: ISkillAcquisitionJobRepository,
        provider_repo: ILibrarianProviderRepository,
        secret_repo: IProviderSecretRepository,
        now_provider: Callable[[], datetime] = now_utc,
    ) -> None:
        """Initialize service dependencies.

        Args:
            repository: Durable job persistence port.
            provider_repo: Provider settings repository.
            secret_repo: Provider secret repository.
            now_provider: Clock boundary for deterministic tests.
        """
        self._repository = repository
        self._provider_repo = provider_repo
        self._secret_repo = secret_repo
        self._now_provider = now_provider

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
        """Create one durable skill-acquisition job.

        Args:
            prompt: Missing-skill acquisition prompt.
            agent_name: Requesting agent.
            project: Optional project scope.
            task_summary: Optional current task summary.
            provider_id: Optional preferred provider.
            librarian_profile_id: Optional librarian profile.

        Returns:
            Created durable job.
        """
        now = self._now_provider()
        selected_provider = await self._selected_provider(provider_id)
        if selected_provider is None:
            status = SkillAcquisitionJobStatus.GUIDANCE_ONLY
            result_summary = _GUIDANCE_SUMMARY
            error_message = None if provider_id is None else "Provider not found"
            completed_at = now
        elif await provider_can_execute(
            selected_provider, self._secret_repo, self._now_provider
        ):
            status = SkillAcquisitionJobStatus.ACCEPTED
            result_summary = _ACCEPTED_SUMMARY
            error_message = None
            completed_at = None
        else:
            status = SkillAcquisitionJobStatus.FAILED
            result_summary = None
            error_message = _CREDENTIAL_FAILURE
            completed_at = now

        job = await self._repository.create(
            SkillAcquisitionJobCreate(
                id=_job_id(prompt=prompt, agent_name=agent_name, now=now),
                prompt=prompt,
                agent_name=agent_name,
                project=project,
                task_summary=task_summary,
                status=status,
                provider_id=None if selected_provider is None else selected_provider.id,
                librarian_profile_id=librarian_profile_id,
                result_summary=result_summary,
                evidence_urls=[],
                error_message=error_message,
                created_at=now,
                updated_at=now,
                completed_at=completed_at,
            )
        )
        return job

    async def get_job(self, job_id: str) -> SkillAcquisitionJob:
        """Return one durable skill-acquisition job.

        Args:
            job_id: Job identifier.

        Returns:
            Matching job.
        """
        job = await self._repository.get(job_id)
        if job is None:
            raise LibrarianResourceNotFoundError(
                f"Skill acquisition job not found: {job_id}"
            )
        return job

    async def complete_job(
        self,
        *,
        job_id: str,
        result_summary: str,
        evidence_urls: list[str] | None = None,
        skill_id: str | None = None,
        context_id: str | None = None,
    ) -> SkillAcquisitionJob:
        """Mark a durable job complete with sanitized result handles.

        Args:
            job_id: Job identifier.
            result_summary: Sanitized result summary.
            evidence_urls: Optional source URLs.
            skill_id: Deprecated persisted skill identifier; normally None after
                SQLite skill CRUD removal.
            context_id: Optional persisted resume context identifier.

        Returns:
            Updated job.
        """
        now = self._now_provider()
        job = await self._repository.update(
            job_id,
            SkillAcquisitionJobUpdate(
                status=SkillAcquisitionJobStatus.COMPLETED,
                result_summary=result_summary,
                evidence_urls=[] if evidence_urls is None else evidence_urls,
                error_message=None,
                skill_id=skill_id,
                context_id=context_id,
                updated_at=now,
                completed_at=now,
            ),
        )
        return job

    async def fail_job(
        self,
        *,
        job_id: str,
        error_message: str,
    ) -> SkillAcquisitionJob:
        """Mark one durable job as failed and sanitize provider failure details.

        Args:
            job_id: Job identifier.
            error_message: Failure message from executor/provider.

        Returns:
            Updated job.
        """
        now = self._now_provider()
        job = await self._repository.update(
            job_id,
            SkillAcquisitionJobUpdate(
                status=SkillAcquisitionJobStatus.FAILED,
                result_summary=None,
                evidence_urls=[],
                error_message=_redact_secret_text(error_message),
                skill_id=None,
                context_id=None,
                updated_at=now,
                completed_at=now,
            ),
        )
        return job

    async def complete_with_skill_artifact(
        self,
        *,
        job_id: str,
        artifact: SkillAcquisitionArtifact,
    ) -> SkillAcquisitionJob:
        """Complete a job from an acquired skill artifact.

        Args:
            job_id: Durable job identifier.
            artifact: Structured acquired skill payload.

        Returns:
            Completed job with no SQLite skill/context record.
        """
        job = await self.get_job(job_id)
        if job.status is SkillAcquisitionJobStatus.COMPLETED:
            return job
        if job.status not in {
            SkillAcquisitionJobStatus.ACCEPTED,
            SkillAcquisitionJobStatus.GUIDANCE_ONLY,
        }:
            raise LibrarianValidationError("Skill acquisition job is not completable")

        evidence_urls = _clean_items(artifact.evidence_urls)
        result_summary = _completion_summary(
            artifact=artifact,
        )
        completed = await self.complete_job(
            job_id=job_id,
            result_summary=result_summary,
            evidence_urls=evidence_urls,
            context_id=None,
        )
        return completed

    async def _selected_provider(
        self,
        provider_id: str | None,
    ) -> LibrarianProvider | None:
        if provider_id is not None:
            return await self._provider_repo.get(provider_id)
        providers = await self._provider_repo.list_all()
        for provider in providers:
            if await provider_can_execute(
                provider, self._secret_repo, self._now_provider
            ):
                return provider
        return None


def _job_id(*, prompt: str, agent_name: str, now: datetime) -> str:
    digest = hashlib.sha256(
        f"{agent_name}:{prompt}:{now.isoformat()}".encode()
    ).hexdigest()
    return f"{_JOB_PREFIX}{digest[:18]}"


def _completion_summary(
    *,
    artifact: SkillAcquisitionArtifact,
) -> str:
    if artifact.source_summary is not None and artifact.source_summary.strip():
        return artifact.source_summary.strip()
    return f"Acquired skill artifact generated: {artifact.title}"


def _clean_items(values: list[str]) -> list[str]:
    return [value.strip() for value in values if value.strip()]


def _redact_secret_text(value: str | None) -> str | None:
    if value is None:
        return None
    return redact_sensitive_text(value)
