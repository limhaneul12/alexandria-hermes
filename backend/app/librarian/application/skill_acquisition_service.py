"""Durable async skill-acquisition job service."""

from __future__ import annotations

import hashlib
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

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
    SkillAcquisitionJobStage,
    SkillAcquisitionJobStatus,
)
from app.librarian.domain.event_enum.skill_acquisition_enums import ItemStatus
from app.librarian.domain.repositories.skill_acquisition_job_repository import (
    ISkillAcquisitionJobRepository,
)
from app.shared.exceptions import (
    LibrarianResourceNotFoundError,
    LibrarianValidationError,
    ObsidianValidationError,
)
from app.shared.types.extra_types import JSONObject
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
_PROMPT_REFERENCE = "Prompts/Task Prompts/Librarian Operating Prompt v0.1.md"
_PROMPT_REFERENCE_HASH = hashlib.sha256(_PROMPT_REFERENCE.encode()).hexdigest()
_LEGACY_DIRECT_START_OVERRIDE = (
    "Direct skill-acquisition start without a search-first snapshot; "
    "recorded for compatibility with legacy callers."
)


class SkillArtifactPublicationError(LibrarianValidationError):
    """Raised when publication fails after partial durable handles exist."""

    def __init__(
        self,
        message: str,
        *,
        skill_id: str | None = None,
        skill_note_path: str | None = None,
        stage: SkillAcquisitionJobStage = SkillAcquisitionJobStage.FAILED,
        reindex_status: str | None = None,
        verification_status: str | None = None,
    ) -> None:
        """Create publication failure with optional saved handles.

        Args:
            message: Sanitized failure message.
            skill_id: Durable skill note id when save already succeeded.
            skill_note_path: Durable skill note path when save already succeeded.
            stage: Observable stage where publication failed.
            reindex_status: Optional reindex status at failure time.
            verification_status: Optional verification status at failure time.
        """
        super().__init__(message)
        self.skill_id = skill_id
        self.skill_note_path = skill_note_path
        self.stage = stage
        self.reindex_status = reindex_status
        self.verification_status = verification_status


@dataclass(frozen=True, slots=True)
class PublishedSkillArtifact:
    """Durable publication result for an acquired skill artifact."""

    skill_id: str
    context_id: str | None = None
    result_summary: str | None = None
    skill_note_path: str | None = None
    stage: SkillAcquisitionJobStage = SkillAcquisitionJobStage.HANDOFF_READY
    progress_summary: str | None = None
    reindex_status: str | None = None
    verification_status: str | None = None
    handoff: JSONObject | None = None
    repair_hint: str | None = None


class SkillArtifactPublisher(Protocol):
    """Boundary for publishing acquired skills to the durable library."""

    async def publish_skill_artifact(
        self,
        *,
        job: SkillAcquisitionJob,
        artifact: SkillAcquisitionArtifact,
    ) -> PublishedSkillArtifact:
        """Publish one acquired skill artifact.

        Args:
            job: Skill-acquisition job being completed.
            artifact: Structured skill artifact.

        Returns:
            Durable skill publication handles.
        """


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
        search_snapshot: JSONObject | None = None,
        acquisition_override_reason: str | None = None,
    ) -> SkillAcquisitionJob:
        """Create one durable skill-acquisition job.

        Args:
            prompt: Missing-skill acquisition prompt.
            agent_name: Requesting agent.
            project: Optional project scope.
            task_summary: Optional current task summary.
            provider_id: Optional preferred provider.
            librarian_profile_id: Optional librarian profile.
            search_snapshot: Optional search-first decision snapshot.
            acquisition_override_reason: Explicit reason for starting without search.

        Returns:
            Created durable job.
        """
        if _search_snapshot_unavailable(search_snapshot):
            raise LibrarianValidationError(
                "Skill acquisition blocked by search readiness: SEARCH_UNAVAILABLE"
            )
        if _search_snapshot_sufficient(search_snapshot):
            raise LibrarianValidationError(
                "Skill acquisition blocked because an existing skill is sufficient"
            )
        now = self._now_provider()
        selected_provider = await self._selected_provider(provider_id)
        override_reason = _override_reason(
            search_snapshot=search_snapshot,
            acquisition_override_reason=acquisition_override_reason,
        )
        if selected_provider is None:
            status = SkillAcquisitionJobStatus.GUIDANCE_ONLY
            result_summary = _GUIDANCE_SUMMARY
            error_message = None if provider_id is None else "Provider not found"
            completed_at = now
            stage = SkillAcquisitionJobStage.GUIDANCE_READY
        elif await provider_can_execute(
            selected_provider, self._secret_repo, self._now_provider
        ):
            status = SkillAcquisitionJobStatus.ACCEPTED
            result_summary = _ACCEPTED_SUMMARY
            error_message = None
            completed_at = None
            stage = SkillAcquisitionJobStage.REQUEST_ACCEPTED
        else:
            status = SkillAcquisitionJobStatus.FAILED
            result_summary = None
            error_message = _CREDENTIAL_FAILURE
            completed_at = now
            stage = SkillAcquisitionJobStage.PROVIDER_FAILED

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
                stage=stage,
                progress_summary=result_summary,
                repair_hint=error_message,
                search_snapshot=search_snapshot,
                acquisition_override_reason=override_reason,
                prompt_reference=_PROMPT_REFERENCE,
                prompt_reference_hash=_PROMPT_REFERENCE_HASH,
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
        skill_note_path: str | None = None,
        stage: SkillAcquisitionJobStage = SkillAcquisitionJobStage.HANDOFF_READY,
        progress_summary: str | None = None,
        reindex_status: str | None = None,
        verification_status: str | None = None,
        handoff: JSONObject | None = None,
        repair_hint: str | None = None,
        search_snapshot: JSONObject | None = None,
        acquisition_override_reason: str | None = None,
        prompt_reference: str | None = None,
        prompt_reference_hash: str | None = None,
    ) -> SkillAcquisitionJob:
        """Mark a durable job complete with sanitized result handles.

        Args:
            job_id: Job identifier.
            result_summary: Sanitized result summary.
            evidence_urls: Optional source URLs.
            skill_id: Deprecated persisted skill identifier; normally None after
                SQLite skill CRUD removal.
            context_id: Optional persisted resume context identifier.
            skill_note_path: Optional Obsidian note path for the saved skill.
            stage: Observable completion-loop stage.
            progress_summary: Human-readable stage summary.
            reindex_status: Post-save index refresh status.
            verification_status: Exact read/search verification status.
            handoff: Structured resume payload for the current task.
            repair_hint: Optional repair guidance when completion is degraded.
            search_snapshot: Optional replacement search-first decision snapshot.
            acquisition_override_reason: Optional replacement override reason.
            prompt_reference: Optional replacement operating prompt reference.
            prompt_reference_hash: Optional replacement operating prompt hash.

        Returns:
            Updated job.
        """
        now = self._now_provider()
        existing = await self.get_job(job_id)
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
                stage=stage,
                progress_summary=progress_summary or result_summary,
                skill_note_path=skill_note_path,
                reindex_status=reindex_status,
                verification_status=verification_status,
                handoff=handoff,
                repair_hint=repair_hint,
                search_snapshot=search_snapshot
                if search_snapshot is not None
                else existing.search_snapshot,
                acquisition_override_reason=acquisition_override_reason
                if acquisition_override_reason is not None
                else existing.acquisition_override_reason,
                prompt_reference=prompt_reference
                if prompt_reference is not None
                else existing.prompt_reference,
                prompt_reference_hash=prompt_reference_hash
                if prompt_reference_hash is not None
                else existing.prompt_reference_hash,
            ),
        )
        return job

    async def fail_job(
        self,
        *,
        job_id: str,
        error_message: str,
        stage: SkillAcquisitionJobStage = SkillAcquisitionJobStage.FAILED,
        progress_summary: str | None = None,
        skill_id: str | None = None,
        skill_note_path: str | None = None,
        reindex_status: str | None = None,
        verification_status: str | None = None,
        repair_hint: str | None = None,
        handoff: JSONObject | None = None,
    ) -> SkillAcquisitionJob:
        """Mark one durable job as failed and sanitize provider failure details.

        Args:
            job_id: Job identifier.
            error_message: Failure message from executor/provider.
            stage: Failure stage to expose on the durable job.
            progress_summary: Optional operator-readable failure progress.
            skill_id: Optional saved skill note id for partial publication.
            skill_note_path: Optional saved skill note path for partial publication.
            reindex_status: Optional reindex status for partial publication.
            verification_status: Optional verification status for partial publication.
            repair_hint: Optional repair hint; defaults to sanitized error.
            handoff: Optional structured retry/repair handoff.

        Returns:
            Updated job.
        """
        now = self._now_provider()
        existing = await self.get_job(job_id)
        sanitized_error = _redact_secret_text(error_message)
        sanitized_repair_hint = _redact_secret_text(repair_hint)
        job = await self._repository.update(
            job_id,
            SkillAcquisitionJobUpdate(
                status=SkillAcquisitionJobStatus.FAILED,
                result_summary=None,
                evidence_urls=[],
                error_message=sanitized_error,
                skill_id=skill_id,
                context_id=None,
                updated_at=now,
                completed_at=now,
                stage=stage,
                progress_summary=progress_summary,
                skill_note_path=skill_note_path,
                reindex_status=reindex_status,
                verification_status=verification_status,
                handoff=handoff,
                repair_hint=sanitized_repair_hint or sanitized_error,
                search_snapshot=existing.search_snapshot,
                acquisition_override_reason=existing.acquisition_override_reason,
                prompt_reference=existing.prompt_reference,
                prompt_reference_hash=existing.prompt_reference_hash,
            ),
        )
        return job

    async def complete_with_skill_artifact(
        self,
        *,
        job_id: str,
        artifact: SkillAcquisitionArtifact,
        artifact_publisher: SkillArtifactPublisher | None = None,
    ) -> SkillAcquisitionJob:
        """Complete a job from an acquired skill artifact.

        Args:
            job_id: Durable job identifier.
            artifact: Structured acquired skill payload.
            artifact_publisher: Optional durable library publisher.

        Returns:
            Completed job with durable skill/context handles when published.
        """
        job = await self.get_job(job_id)
        if job.status is SkillAcquisitionJobStatus.COMPLETED:
            return job
        if job.status not in {
            SkillAcquisitionJobStatus.ACCEPTED,
            SkillAcquisitionJobStatus.GUIDANCE_ONLY,
        }:
            raise LibrarianValidationError("Skill acquisition job is not completable")
        if artifact.activate or artifact.status is ItemStatus.ACTIVE:
            raise LibrarianValidationError(
                "Skill acquisition artifacts cannot be auto-activated"
            )

        evidence_urls = _clean_items(artifact.evidence_urls)
        result_summary = _completion_summary(
            artifact=artifact,
        )
        skill_id: str | None = None
        context_id: str | None = None
        skill_note_path: str | None = None
        stage = SkillAcquisitionJobStage.ARTIFACT_RECEIVED
        progress_summary = result_summary
        reindex_status: str | None = None
        verification_status: str | None = None
        handoff: JSONObject | None = None
        repair_hint: str | None = None
        if artifact_publisher is not None:
            try:
                published = await artifact_publisher.publish_skill_artifact(
                    job=job,
                    artifact=artifact,
                )
            except LibrarianValidationError as error:
                failure_stage = _publication_failure_stage(error)
                return await self.fail_job(
                    job_id=job.id,
                    error_message=str(error),
                    stage=failure_stage,
                    progress_summary="Skill artifact publication failed validation.",
                    skill_id=_publication_error_skill_id(error),
                    skill_note_path=_publication_error_skill_note_path(error),
                    reindex_status=_publication_error_reindex_status(error),
                    verification_status=_publication_error_verification_status(error),
                    repair_hint=str(error),
                    handoff=_repair_handoff(
                        job=job,
                        error_message=str(error),
                        stage=failure_stage,
                        skill_id=_publication_error_skill_id(error),
                        skill_note_path=_publication_error_skill_note_path(error),
                    ),
                )
            except ObsidianValidationError as error:
                return await self.fail_job(
                    job_id=job.id,
                    error_message=str(error),
                    progress_summary="Skill artifact publication was blocked by Obsidian guardrails.",
                    repair_hint=str(error),
                    handoff=_repair_handoff(job=job, error_message=str(error)),
                )
            except Exception:
                return await self.fail_job(
                    job_id=job.id,
                    error_message="Skill artifact publication failed",
                    progress_summary="Skill artifact publication failed unexpectedly.",
                    repair_hint="Retry completion after checking Obsidian save/search readiness.",
                    handoff=_repair_handoff(
                        job=job,
                        error_message="Skill artifact publication failed",
                    ),
                )
            validation_error = _completion_handoff_error(published.handoff)
            if validation_error is not None:
                return await self.fail_job(
                    job_id=job.id,
                    error_message=validation_error,
                    progress_summary="Skill acquisition handoff failed validation.",
                    repair_hint=validation_error,
                    handoff=_repair_handoff(job=job, error_message=validation_error),
                )
            skill_id = published.skill_id
            context_id = published.context_id
            skill_note_path = published.skill_note_path
            stage = published.stage
            progress_summary = published.progress_summary or published.result_summary
            reindex_status = published.reindex_status
            verification_status = published.verification_status
            handoff = published.handoff
            repair_hint = published.repair_hint
            if published.result_summary is not None:
                result_summary = published.result_summary
        completed = await self.complete_job(
            job_id=job_id,
            result_summary=result_summary,
            evidence_urls=evidence_urls,
            skill_id=skill_id,
            context_id=context_id,
            skill_note_path=skill_note_path,
            stage=stage,
            progress_summary=progress_summary,
            reindex_status=reindex_status,
            verification_status=verification_status,
            handoff=handoff,
            repair_hint=repair_hint,
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


def _search_snapshot_unavailable(search_snapshot: JSONObject | None) -> bool:
    if search_snapshot is None:
        return False
    if search_snapshot.get("decision") == "SEARCH_UNAVAILABLE":
        return True
    handoff = search_snapshot.get("handoff")
    if isinstance(handoff, dict):
        return handoff.get("decision") == "skill_search_repair_required"
    return False


def _search_snapshot_sufficient(search_snapshot: JSONObject | None) -> bool:
    if search_snapshot is None:
        return False
    return search_snapshot.get("decision") == "FOUND_SUFFICIENT"


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


def _override_reason(
    *,
    search_snapshot: JSONObject | None,
    acquisition_override_reason: str | None,
) -> str | None:
    if search_snapshot is not None:
        return None
    if acquisition_override_reason is not None and acquisition_override_reason.strip():
        return acquisition_override_reason.strip()
    return _LEGACY_DIRECT_START_OVERRIDE


def _publication_failure_stage(
    error: LibrarianValidationError,
) -> SkillAcquisitionJobStage:
    if isinstance(error, SkillArtifactPublicationError):
        return error.stage
    normalized = str(error).lower()
    if "read-back" in normalized or "search" in normalized or "verified" in normalized:
        return SkillAcquisitionJobStage.SKILL_SAVED
    return SkillAcquisitionJobStage.FAILED


def _publication_error_skill_id(error: LibrarianValidationError) -> str | None:
    if isinstance(error, SkillArtifactPublicationError):
        return error.skill_id
    return None


def _publication_error_skill_note_path(error: LibrarianValidationError) -> str | None:
    if isinstance(error, SkillArtifactPublicationError):
        return error.skill_note_path
    return None


def _publication_error_reindex_status(error: LibrarianValidationError) -> str | None:
    if isinstance(error, SkillArtifactPublicationError):
        return error.reindex_status
    return None


def _publication_error_verification_status(
    error: LibrarianValidationError,
) -> str | None:
    if isinstance(error, SkillArtifactPublicationError):
        return error.verification_status
    return None


def _completion_handoff_error(handoff: JSONObject | None) -> str | None:
    if handoff is None:
        return "Skill acquisition handoff is required"
    required_fields = (
        "current_task",
        "evidence",
        "job",
        "persistence",
        "progress_summary",
        "skill",
    )
    missing_fields = sorted(field for field in required_fields if field not in handoff)
    if missing_fields:
        return "Skill acquisition handoff missing required fields: " + ", ".join(
            missing_fields
        )
    if (
        not isinstance(handoff["progress_summary"], str)
        or not handoff["progress_summary"].strip()
    ):
        return "Skill acquisition handoff progress_summary is required"
    evidence = handoff["evidence"]
    if not isinstance(evidence, list):
        return "Skill acquisition handoff evidence must be a list"
    skill = handoff["skill"]
    if not isinstance(skill, dict):
        return "Skill acquisition handoff skill must be an object"
    missing_skill_fields = sorted(
        field for field in ("id", "path", "status") if field not in skill
    )
    if missing_skill_fields:
        return "Skill acquisition handoff skill missing required fields: " + ", ".join(
            missing_skill_fields
        )
    persistence = handoff["persistence"]
    if not isinstance(persistence, dict):
        return "Skill acquisition handoff persistence must be an object"
    missing_persistence_fields = sorted(
        field
        for field in ("reindex_status", "saved", "verified")
        if field not in persistence
    )
    if missing_persistence_fields:
        return (
            "Skill acquisition handoff persistence missing required fields: "
            + ", ".join(missing_persistence_fields)
        )
    if persistence.get("saved") is not True or persistence.get("verified") is not True:
        return "Skill acquisition handoff persistence must be saved and verified"
    current_task = handoff["current_task"]
    if not isinstance(current_task, dict):
        return "Skill acquisition handoff current_task must be an object"
    missing_task_fields = sorted(
        field
        for field in ("next_steps", "resume_summary", "stop_condition")
        if field not in current_task
    )
    if missing_task_fields:
        return (
            "Skill acquisition handoff current_task missing required fields: "
            + ", ".join(missing_task_fields)
        )
    if (
        not isinstance(current_task["resume_summary"], str)
        or not current_task["resume_summary"].strip()
    ):
        return "Skill acquisition handoff current_task resume_summary is required"
    if not isinstance(current_task["next_steps"], list):
        return "Skill acquisition handoff current_task next_steps must be a list"
    if (
        not isinstance(current_task["stop_condition"], str)
        or not current_task["stop_condition"].strip()
    ):
        return "Skill acquisition handoff current_task stop_condition is required"
    return None


def _repair_handoff(
    *,
    job: SkillAcquisitionJob,
    error_message: str,
    stage: SkillAcquisitionJobStage = SkillAcquisitionJobStage.FAILED,
    skill_id: str | None = None,
    skill_note_path: str | None = None,
) -> JSONObject:
    payload: JSONObject = {
        "decision": "skill_acquisition_repair_required",
        "job": {
            "id": job.id,
            "status": SkillAcquisitionJobStatus.FAILED.value,
            "stage": stage.value,
        },
        "repair": {
            "retry_key": job.id,
            "hint": _redact_secret_text(error_message)
            or "Retry skill acquisition completion.",
        },
    }
    if skill_id is not None or skill_note_path is not None:
        payload["saved_handles"] = {
            "skill_id": skill_id,
            "skill_note_path": skill_note_path,
        }
    return payload
