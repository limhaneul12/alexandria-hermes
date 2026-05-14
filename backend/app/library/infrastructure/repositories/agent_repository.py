"""SQLAlchemy agent profile repository."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import cast

from app.library.domain.contracts.agent_contracts import AgentCreate, AgentUpdate
from app.library.domain.entities.read_models import AgentProfile
from app.library.domain.repositories.agent_repository import IAgentRepository
from app.library.infrastructure.models.agent_models import AgentProfileORM
from app.shared.exceptions import NotFoundError
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession


def _to_read_model(row: AgentProfileORM) -> AgentProfile:
    """Map an agent ORM row into the domain read model."""
    return AgentProfile(
        id=row.id,
        name=row.name,
        provider=row.provider,
        description=row.description,
        capabilities=list(row.capabilities),
        preferred_librarian_provider=row.preferred_librarian_provider,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


class SqlAlchemyAgentRepository(IAgentRepository):
    """Persistence operations for agent profiles."""

    def __init__(self, *, session: AsyncSession) -> None:
        """Initialize repository.

        Args:
            session: Active async session.
        """
        self._session = session

    async def create(self, payload: AgentCreate) -> AgentProfile:
        """Create an agent profile.

        Args:
            payload [AgentCreate]: Value supplied to create.

        Returns:
            AgentProfile: Value produced by create.
        """
        model = AgentProfileORM(**payload.to_record())
        self._session.add(model)
        await self._session.flush()
        return _to_read_model(model)

    async def get(self, agent_id: str) -> AgentProfile | None:
        """Get one profile by PK.

        Args:
            agent_id [str]: Value supplied to get.

        Returns:
            AgentProfile | None: Value produced by get.
        """
        model = await self._session.get(AgentProfileORM, agent_id)
        return None if model is None else _to_read_model(model)

    async def list_all(self) -> list[AgentProfile]:
        """List all profiles.

        Returns:
            list[AgentProfile]: Value produced by list_all.
        """
        rows = await self._session.execute(select(AgentProfileORM))
        return [_to_read_model(row) for row in rows.scalars().all()]

    async def update(self, agent_id: str, payload: AgentUpdate) -> AgentProfile:
        """Patch profile fields.

        Args:
            agent_id [str]: Value supplied to update.
            payload [AgentUpdate]: Value supplied to update.

        Returns:
            AgentProfile: Value produced by update.
        """
        model = await self._session.get(AgentProfileORM, agent_id)
        if model is None:
            raise NotFoundError(f"Agent not found: {agent_id}")

        values = payload.to_record()
        if "description" in values:
            model.description = cast(str | None, values["description"])
        if "capabilities" in values:
            model.capabilities = cast(list[str], values["capabilities"])
        model.updated_at = datetime.now(UTC)
        await self._session.flush()
        return _to_read_model(model)

    async def delete(self, agent_id: str) -> None:
        """Delete one agent profile.

        Args:
            agent_id [str]: Value supplied to delete.
        """
        model = await self._session.get(AgentProfileORM, agent_id)
        if model is None:
            raise NotFoundError(f"Agent not found: {agent_id}")

        await self._session.execute(
            delete(AgentProfileORM).where(AgentProfileORM.id == agent_id)
        )
        await self._session.flush()
