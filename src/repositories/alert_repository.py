from sqlalchemy.ext.asyncio import AsyncSession

from src.models import Alert
from src.repositories.base import BaseRepository


class AlertRepository(BaseRepository[Alert]):
    def __init__(self, session: AsyncSession):
        super().__init__(session, Alert)
