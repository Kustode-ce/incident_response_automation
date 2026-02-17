from __future__ import annotations

from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from src.models import Incident, Runbook
from src.repositories import IncidentRepository, RunbookRepository
from src.services.audit_logger import AuditLogger


class MitigationSelector:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.incidents = IncidentRepository(session)
        self.runbooks = RunbookRepository(session)
        self.audit_logger = AuditLogger(session)

    async def select_runbook(self, incident: Incident) -> Optional[Runbook]:
        runbooks = await self.runbooks.list(limit=200, offset=0)
        if not runbooks:
            return None

        def score(runbook: Runbook) -> int:
            score_value = 0
            tags = set(runbook.tags or [])
            if incident.severity.value in tags:
                score_value += 2
            if incident.category.value in tags:
                score_value += 2
            if "mitigation" in tags:
                score_value += 1
            return score_value

        selected = max(runbooks, key=score)
        await self.audit_logger.log(
            action="mitigation_playbook_selected",
            actor="system",
            status="ok",
            details={
                "incident_id": str(incident.id),
                "runbook_id": str(selected.id),
                "runbook_name": selected.name,
            },
            incident_id=incident.id,
        )
        return selected
