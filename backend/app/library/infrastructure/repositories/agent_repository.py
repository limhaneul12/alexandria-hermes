"""SQLAlchemy agent profile repository."""

from __future__ import annotations

from datetime import UTC, datetime

from app.library.domain.entities.read_models import AgentProfile
from app.library.domain.repositories.agent_repository import AgentRepository
from app.library.infrastructure.models.agent import AgentProfileORM
from app.shared.exceptions import NotFoundError
from app.shared.types.extra_types import JSONValue
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


class SqlAlchemyAgentRepository(AgentRepository):
    """Persistence operations for agent profiles."""

    def __init__(self, *, session: AsyncSession) -> None:
        """Initialize repository.

        Args:
            session: Active async session.
        """
        self._session = session

    async def create(self, payload: dict[str, JSONValue]) -> AgentProfile:
        """Create an agent profile."""
        model = AgentProfileORM(**payload)
        self._session.add(model)
        await self._session.flush()
        return _to_read_model(model)

    async def get(self, agent_id: int) -> AgentProfile | None:
        """Get one profile by PK."""
        model = await self._session.get(AgentProfileORM, agent_id)
        return None if model is None else _to_read_model(model)

    async def list_all(self) -> list[AgentProfile]:
        """List all profiles."""
        rows = await self._session.execute(select(AgentProfileORM))
        return [_to_read_model(row) for row in rows.scalars().all()]

    async def update(
        self, agent_id: int, payload: dict[str, JSONValue]
    ) -> AgentProfile:
        """Patch profile fields."""
        model = await self._session.get(AgentProfileORM, agent_id)
        if model is None:
            raise NotFoundError(f"Agent not found: {agent_id}")

        for key, value in payload.items():
            setattr(model, key, value)
        model.updated_at = datetime.now(UTC)
        await self._session.flush()
        return _to_read_model(model)

    async def delete(self, agent_id: int) -> None:
        """Delete one agent profile."""
        model = await self._session.get(AgentProfileORM, agent_id)
        if model is None:
            raise NotFoundError(f"Agent not found: {agent_id}")

        await self._session.execute(
            delete(AgentProfileORM).where(AgentProfileORM.id == agent_id)
        )
        await self._session.flush()
