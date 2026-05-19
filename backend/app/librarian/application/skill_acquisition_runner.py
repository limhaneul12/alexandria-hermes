"""Background runner for async skill-acquisition execution."""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass

from app.librarian.application.skill_acquisition_service import SkillAcquisitionService
from app.librarian.domain.contracts.skill_acquisition_contracts import (
    SkillAcquisitionArtifact,
)
from app.librarian.domain.entities.skill_acquisition_job import SkillAcquisitionJob
from app.librarian.domain.event_enum.collaboration_enums import (
    SkillAcquisitionJobStatus,
)

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True, kw_only=True)
class SkillAcquisitionExecutionRequest:
    """Normalized command for one acquisition execution attempt."""

    job_id: str
    prompt: str
    agent_name: str
    project: str | None
    task_summary: str | None
    provider_id: str | None
    librarian_profile_id: str | None


class ISkillAcquisitionExecutor(ABC):
    """Interface for an async acquisition executor."""

    @abstractmethod
    async def acquire_skill(
        self,
        request: SkillAcquisitionExecutionRequest,
    ) -> SkillAcquisitionArtifact:
        """Execute one acquisition and return the extracted artifact.

        Args:
            request: Normalized acquisition execution command.

        Returns:
            Extracted skill-acquisition artifact.
        """


class SkillAcquisitionRunner:
    """Drive one durable skill-acquisition job through execution."""

    def __init__(
        self,
        *,
        service: SkillAcquisitionService,
        executor: ISkillAcquisitionExecutor,
    ) -> None:
        """Create the runner with service/executor seam dependencies.

        Args:
            service: Skill-acquisition durable state service.
            executor: Async acquisition executor facade.
        """
        self._service = service
        self._executor = executor

    async def run_job(self, job_id: str) -> SkillAcquisitionJob:
        """Execute one job when acceptable and persist outcomes.

        Args:
            job_id: Durable acquisition job identifier.

        Returns:
            Updated durable job.
        """
        job = await self._service.get_job(job_id)
        if job.status is not SkillAcquisitionJobStatus.ACCEPTED:
            return job

        request = SkillAcquisitionExecutionRequest(
            job_id=job.id,
            prompt=job.prompt,
            agent_name=job.agent_name,
            project=job.project,
            task_summary=job.task_summary,
            provider_id=job.provider_id,
            librarian_profile_id=job.librarian_profile_id,
        )

        try:
            artifact = await self._executor.acquire_skill(request)
        except Exception as error:
            logger.warning(
                "Skill acquisition executor failed",
                extra={"job_id": job.id, "error_type": type(error).__name__},
            )
            return await self._service.fail_job(
                job_id=job.id,
                error_message="Skill acquisition executor failed",
            )

        return await self._service.complete_with_skill_artifact(
            job_id=job.id,
            artifact=artifact,
        )
