from sqlalchemy.ext.asyncio import AsyncSession

from src.models import ApprovalRequest
from src.repositories.base import BaseRepository


class ApprovalRepository(BaseRepository[ApprovalRequest]):
    def __init__(self, session: AsyncSession):
        super().__init__(session, ApprovalRequest)
