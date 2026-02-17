from __future__ import annotations

from typing import Any, Dict, Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.models import AuditLog
from src.repositories import AuditLogRepository


class AuditLogger:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.repo = AuditLogRepository(session)

    async def log(
        self,
        action: str,
        actor: str = "system",
        status: str = "ok",
        details: Optional[Dict[str, Any]] = None,
        incident_id: Optional[UUID] = None,
        runbook_execution_id: Optional[UUID] = None,
    ) -> AuditLog:
        entry = AuditLog(
            action=action,
            actor=actor,
            status=status,
            details=details or {},
            incident_id=incident_id,
            runbook_execution_id=runbook_execution_id,
        )
        await self.repo.create(entry)
        return entry
