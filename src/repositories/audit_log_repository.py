from sqlalchemy.ext.asyncio import AsyncSession

from src.models import AuditLog
from src.repositories.base import BaseRepository


class AuditLogRepository(BaseRepository[AuditLog]):
    def __init__(self, session: AsyncSession):
        super().__init__(session, AuditLog)
