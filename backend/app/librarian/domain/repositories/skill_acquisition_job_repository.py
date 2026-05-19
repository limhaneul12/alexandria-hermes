"""Skill-acquisition job repository abstraction."""

from __future__ import annotations

from abc import ABC, abstractmethod

from app.librarian.domain.contracts.skill_acquisition_contracts import (
    SkillAcquisitionJobCreate,
    SkillAcquisitionJobUpdate,
)
from app.librarian.domain.entities.skill_acquisition_job import SkillAcquisitionJob


class ISkillAcquisitionJobRepository(ABC):
    """Persistence contract for durable skill-acquisition jobs."""

    @abstractmethod
    async def create(self, payload: SkillAcquisitionJobCreate) -> SkillAcquisitionJob:
        """Create one job.

        Args:
            payload: Job creation payload.

        Returns:
            Created job read model.
        """

    @abstractmethod
    async def get(self, job_id: str) -> SkillAcquisitionJob | None:
        """Get one job.

        Args:
            job_id: Job identifier.

        Returns:
            Matching job or ``None``.
        """

    @abstractmethod
    async def update(
        self,
        job_id: str,
        payload: SkillAcquisitionJobUpdate,
    ) -> SkillAcquisitionJob:
        """Update one job.

        Args:
            job_id: Job identifier.
            payload: Job update payload.

        Returns:
            Updated job read model.
        """
