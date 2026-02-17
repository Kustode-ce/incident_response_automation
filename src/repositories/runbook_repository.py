from sqlalchemy.ext.asyncio import AsyncSession

from src.models import Runbook, RunbookExecution
from src.repositories.base import BaseRepository


class RunbookRepository(BaseRepository[Runbook]):
    def __init__(self, session: AsyncSession):
        super().__init__(session, Runbook)


class RunbookExecutionRepository(BaseRepository[RunbookExecution]):
    def __init__(self, session: AsyncSession):
        super().__init__(session, RunbookExecution)
