from sqlalchemy.ext.asyncio import AsyncSession

from src.models import Integration
from src.repositories.base import BaseRepository


class IntegrationRepository(BaseRepository[Integration]):
    def __init__(self, session: AsyncSession):
        super().__init__(session, Integration)
