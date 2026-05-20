"""SQLAlchemy repository for durable skill-acquisition jobs."""

from __future__ import annotations

from typing import cast

from app.librarian.domain.contracts.skill_acquisition_contracts import (
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
from app.librarian.infrastructure.models.skill_acquisition_job_models import (
    SkillAcquisitionJobORM,
)
from app.shared.exceptions import LibrarianResourceNotFoundError
from app.shared.types.types_convert_utils import aware_utc_datetime
from sqlalchemy.ext.asyncio import AsyncSession


def _to_read_model(row: SkillAcquisitionJobORM) -> SkillAcquisitionJob:
    """Map one ORM row into the domain read model.

    Args:
        row: Persisted skill-acquisition job row.

    Returns:
        Skill-acquisition job read model.
    """
    return SkillAcquisitionJob(
        id=row.id,
        prompt=row.prompt,
        agent_name=row.agent_name,
        project=row.project,
        task_summary=row.task_summary,
        status=SkillAcquisitionJobStatus(row.status),
        provider_id=row.provider_id,
        librarian_profile_id=row.librarian_profile_id,
        skill_id=row.skill_id,
        context_id=row.context_id,
        result_summary=row.result_summary,
        evidence_urls=list(row.evidence_urls),
        error_message=row.error_message,
        created_at=aware_utc_datetime(row.created_at),
        updated_at=aware_utc_datetime(row.updated_at),
        completed_at=aware_utc_datetime(row.completed_at)
        if row.completed_at is not None
        else None,
    )


class SqlAlchemySkillAcquisitionJobRepository(ISkillAcquisitionJobRepository):
    """Persistence operations for durable skill-acquisition jobs."""

    def __init__(self, *, session: AsyncSession) -> None:
        """Initialize repository.

        Args:
            session: Active async session.
        """
        self._session = session

    async def create(self, payload: SkillAcquisitionJobCreate) -> SkillAcquisitionJob:
        """Create one durable job.

        Args:
            payload: Job creation payload.

        Returns:
            Created job read model.
        """
        model = SkillAcquisitionJobORM(
            id=payload.id,
            prompt=payload.prompt,
            agent_name=payload.agent_name,
            project=payload.project,
            task_summary=payload.task_summary,
            status=payload.status.value,
            provider_id=payload.provider_id,
            librarian_profile_id=payload.librarian_profile_id,
            skill_id=payload.skill_id,
            context_id=payload.context_id,
            result_summary=payload.result_summary,
            evidence_urls=list(payload.evidence_urls),
            error_message=payload.error_message,
            created_at=payload.created_at,
            updated_at=payload.updated_at,
            completed_at=payload.completed_at,
        )
        self._session.add(model)
        await self._session.flush()
        return _to_read_model(model)

    async def get(self, job_id: str) -> SkillAcquisitionJob | None:
        """Get one durable job.

        Args:
            job_id: Job identifier.

        Returns:
            Matching job or ``None``.
        """
        model = await self._session.get(SkillAcquisitionJobORM, job_id)
        if model is None:
            return None
        return _to_read_model(model)

    async def update(
        self,
        job_id: str,
        payload: SkillAcquisitionJobUpdate,
    ) -> SkillAcquisitionJob:
        """Update one durable job.

        Args:
            job_id: Job identifier.
            payload: Job update payload.

        Returns:
            Updated job read model.
        """
        model = await self._session.get(SkillAcquisitionJobORM, job_id)
        if model is None:
            raise LibrarianResourceNotFoundError(
                f"Skill acquisition job not found: {job_id}"
            )
        model.status = payload.status.value
        model.result_summary = payload.result_summary
        model.evidence_urls = cast(list[str], list(payload.evidence_urls))
        model.error_message = payload.error_message
        model.skill_id = payload.skill_id
        model.context_id = payload.context_id
        model.updated_at = payload.updated_at
        model.completed_at = payload.completed_at
        await self._session.flush()
        return _to_read_model(model)
