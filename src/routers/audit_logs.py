from typing import List

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.schemas import AuditLogResponse
from src.repositories import AuditLogRepository
from src.utils.database import get_db_session

router = APIRouter(prefix="/audit-logs", tags=["AuditLogs"])


async def _repo(session: AsyncSession) -> AuditLogRepository:
    return AuditLogRepository(session)


@router.get("/", response_model=List[AuditLogResponse])
async def list_audit_logs(
    limit: int = 100,
    offset: int = 0,
    session: AsyncSession = Depends(get_db_session),
):
    repo = await _repo(session)
    logs = await repo.list(limit=limit, offset=offset)
    return [
        AuditLogResponse(
            id=log.id,
            incident_id=log.incident_id,
            runbook_execution_id=log.runbook_execution_id,
            action=log.action,
            actor=log.actor,
            status=log.status,
            details=log.details,
            created_at=log.created_at,
        )
        for log in logs
    ]
