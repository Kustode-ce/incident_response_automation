from typing import Iterable
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.models import Incident
from src.repositories.base import BaseRepository


class IncidentRepository(BaseRepository[Incident]):
    def __init__(self, session: AsyncSession):
        super().__init__(session, Incident)

    async def get(self, entity_id: UUID) -> Incident | None:
        """Get incident with eagerly loaded relationships."""
        result = await self.session.execute(
            select(Incident)
            .where(Incident.id == entity_id)
            .options(
                selectinload(Incident.alerts),
                selectinload(Incident.runbook_executions),
                selectinload(Incident.ml_insights),
            )
        )
        return result.scalar_one_or_none()

    async def list(self, limit: int = 100, offset: int = 0) -> Iterable[Incident]:
        """List incidents with eagerly loaded relationships."""
        result = await self.session.execute(
            select(Incident)
            .options(
                selectinload(Incident.alerts),
                selectinload(Incident.runbook_executions),
                selectinload(Incident.ml_insights),
            )
            .limit(limit)
            .offset(offset)
        )
        return result.scalars().all()
