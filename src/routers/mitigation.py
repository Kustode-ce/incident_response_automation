from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.schemas import RunbookResponse
from src.repositories import IncidentRepository
from src.services.mitigation_selector import MitigationSelector
from src.utils.database import get_db_session

router = APIRouter(prefix="/mitigation", tags=["Mitigation"])


@router.get("/incidents/{incident_id}", response_model=RunbookResponse)
async def recommend_runbook(
    incident_id: UUID,
    session: AsyncSession = Depends(get_db_session),
):
    incidents = IncidentRepository(session)
    incident = await incidents.get(incident_id)
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")

    selector = MitigationSelector(session)
    runbook = await selector.select_runbook(incident)
    if not runbook:
        raise HTTPException(status_code=404, detail="No runbook found")

    return RunbookResponse(
        id=runbook.id,
        name=runbook.name,
        description=runbook.description,
        version=runbook.version,
        enabled=runbook.enabled,
        trigger_conditions=runbook.trigger_conditions,
        steps=runbook.steps,
        rollback_steps=runbook.rollback_steps,
        created_by=runbook.created_by,
        created_at=runbook.created_at,
        updated_at=runbook.updated_at,
        tags=runbook.tags,
        auto_execute=runbook.auto_execute,
        max_concurrent_executions=runbook.max_concurrent_executions,
    )
