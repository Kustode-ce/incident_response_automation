from sqlalchemy.ext.asyncio import AsyncSession

from src.models import MLInsight
from src.repositories.base import BaseRepository


class MLInsightRepository(BaseRepository[MLInsight]):
    def __init__(self, session: AsyncSession):
        super().__init__(session, MLInsight)
