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
from app.library.application.skill_service import SkillService
from app.library.domain.event_enum.item_enums import ItemStatus
from app.memory.application.context_service import ContextService
from app.memory.domain.entities.context_read_models import ContextRecord
from app.shared.exceptions import NotFoundError, ValidationError
from app.shared.types.types_convert_utils import now_utc

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
        skill_service: SkillService,
        context_service: ContextService,
        now_provider: Callable[[], datetime] = now_utc,
    ) -> None:
        """Initialize service dependencies.

        Args:
            repository: Durable job persistence port.
            provider_repo: Provider settings repository.
            secret_repo: Provider secret repository.
            skill_service: Existing library skill submission use case.
            context_service: Context Vault service for resume packets.
            now_provider: Clock boundary for deterministic tests.
        """
        self._repository = repository
        self._provider_repo = provider_repo
        self._secret_repo = secret_repo
        self._skill_service = skill_service
        self._context_service = context_service
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
            raise NotFoundError(f"Skill acquisition job not found: {job_id}")
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
            skill_id: Optional persisted skill identifier.
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

    async def complete_with_skill_artifact(
        self,
        *,
        job_id: str,
        artifact: SkillAcquisitionArtifact,
    ) -> SkillAcquisitionJob:
        """Persist an acquired skill and capture the resume packet for the job.

        Args:
            job_id: Durable job identifier.
            artifact: Structured acquired skill payload.

        Returns:
            Completed job with persisted skill/context handles.
        """
        job = await self.get_job(job_id)
        if job.status is SkillAcquisitionJobStatus.COMPLETED:
            return job
        if job.status not in {
            SkillAcquisitionJobStatus.ACCEPTED,
            SkillAcquisitionJobStatus.GUIDANCE_ONLY,
        }:
            raise ValidationError("Skill acquisition job is not completable")

        evidence_urls = _clean_items(artifact.evidence_urls)
        created_by_name = _created_by_name(job, artifact)
        skill = await self._skill_service.create_skill_by_agent(
            title=artifact.title,
            content=artifact.content,
            summary=artifact.summary,
            category_id=artifact.category_id,
            tags=_completion_tags(artifact.tags),
            purpose=artifact.purpose,
            input_schema=artifact.input_schema,
            output_schema=artifact.output_schema,
            usage_example=artifact.usage_example,
            required_tools=_clean_items(artifact.required_tools),
            risk_level=artifact.risk_level,
            version=artifact.version,
            created_by_name=created_by_name,
            activate=artifact.activate,
            status=artifact.status,
            evidence_urls=evidence_urls,
            source_summary=artifact.source_summary,
        )
        resume_context = await _capture_resume_packet(
            context_service=self._context_service,
            job=job,
            skill_id=skill["id"],
            skill_title=skill["title"],
            artifact=artifact,
            evidence_urls=evidence_urls,
        )
        result_summary = _completion_summary(
            skill_title=skill["title"],
            artifact=artifact,
        )
        completed = await self.complete_job(
            job_id=job_id,
            result_summary=result_summary,
            evidence_urls=evidence_urls,
            skill_id=skill["id"],
            context_id=resume_context.id,
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


async def _capture_resume_packet(
    *,
    context_service: ContextService,
    job: SkillAcquisitionJob,
    skill_id: str,
    skill_title: str,
    artifact: SkillAcquisitionArtifact,
    evidence_urls: list[str],
) -> ContextRecord:
    next_steps = _clean_items(artifact.next_steps)
    if not next_steps:
        next_steps = [
            f"Review and apply skill {skill_id} to the original missing capability.",
            "Archive or supersede the skill later if it is not reusable.",
        ]
    context = await context_service.prepare_compact(
        current_goal=f"Resume after skill acquisition job {job.id}",
        completed=[
            f"Original prompt: {job.prompt}",
            f"Persisted acquired skill: {skill_title} ({skill_id})",
            f"Source summary: {_optional_text(artifact.source_summary)}",
            f"Evidence URLs: {_joined_or_not_recorded(evidence_urls)}",
        ],
        in_progress=_job_task_lines(job),
        key_decisions=[
            "Persisted the acquired capability through the existing agent skill submission path.",
            f"Skill publication status: {ItemStatus(artifact.status).value}",
        ],
        next_actions=next_steps,
        risks=[
            "Agent/librarian-authored skills should be reviewed before high-risk use.",
        ],
        project=job.project,
        source_agent=job.agent_name,
    )
    return context


def _created_by_name(
    job: SkillAcquisitionJob,
    artifact: SkillAcquisitionArtifact,
) -> str:
    if artifact.created_by_name is not None and artifact.created_by_name.strip():
        return artifact.created_by_name.strip()
    return job.agent_name


def _completion_tags(tags: list[str]) -> list[str]:
    return sorted(
        {
            "skill-acquisition",
            *[tag.strip() for tag in tags if tag.strip()],
        }
    )


def _completion_summary(
    *,
    skill_title: str,
    artifact: SkillAcquisitionArtifact,
) -> str:
    if artifact.source_summary is not None and artifact.source_summary.strip():
        return artifact.source_summary.strip()
    return f"Acquired skill persisted: {skill_title}"


def _job_task_lines(job: SkillAcquisitionJob) -> list[str]:
    lines: list[str] = []
    if job.task_summary is not None and job.task_summary.strip():
        lines.append(f"Task summary: {job.task_summary.strip()}")
    if job.provider_id is not None:
        lines.append(f"Provider: {job.provider_id}")
    if not lines:
        lines.append("Return to the original task with the persisted skill available.")
    return lines


def _joined_or_not_recorded(values: list[str]) -> str:
    if not values:
        return "Not recorded."
    return ", ".join(values)


def _optional_text(value: str | None) -> str:
    if value is None or not value.strip():
        return "Not recorded."
    return value.strip()


def _clean_items(values: list[str]) -> list[str]:
    return [value.strip() for value in values if value.strip()]
