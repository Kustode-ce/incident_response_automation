from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from src.models import Incident
from src.observability.unified_observability import record_incident_created
from src.models.schemas import IncidentCreate, IncidentResponse, IncidentUpdate
from src.repositories import IncidentRepository
from src.utils.database import get_db_session

router = APIRouter(prefix="/incidents", tags=["Incidents"])


async def _repo(session: AsyncSession) -> IncidentRepository:
    return IncidentRepository(session)


@router.post("/", response_model=IncidentResponse)
async def create_incident(
    payload: IncidentCreate,
    session: AsyncSession = Depends(get_db_session),
):
    repo = await _repo(session)
    # Convert schema to model fields (extra_data for model, metadata for schema)
    model_data = payload.model_dump(by_alias=False)
    incident = Incident(**model_data)
    await repo.create(incident)
    try:
        record_incident_created(
            severity=str(incident.severity),
            category=str(incident.category),
            source=payload.extra_data.get("source", "api"),
        )
    except Exception:
        pass
    return IncidentResponse(
        id=incident.id,
        fingerprint=incident.fingerprint,
        title=incident.title,
        description=incident.description,
        category=incident.category,
        severity=incident.severity,
        status=incident.status,
        labels=incident.labels,
        metadata=incident.extra_data,
        assigned_to=incident.assigned_to,
        created_by=incident.created_by,
        created_at=incident.created_at,
        updated_at=incident.updated_at,
        resolved_at=incident.resolved_at,
        closed_at=incident.closed_at,
        slack_thread_ts=incident.slack_thread_ts,
        pagerduty_incident_id=incident.pagerduty_incident_id,
        alert_ids=[],
        runbook_execution_ids=[],
    )


@router.get("/", response_model=List[IncidentResponse])
async def list_incidents(
    limit: int = 100,
    offset: int = 0,
    session: AsyncSession = Depends(get_db_session),
):
    repo = await _repo(session)
    incidents = await repo.list(limit=limit, offset=offset)
    responses = []
    for incident in incidents:
        responses.append(
            IncidentResponse(
                id=incident.id,
                fingerprint=incident.fingerprint,
                title=incident.title,
                description=incident.description,
                category=incident.category,
                severity=incident.severity,
                status=incident.status,
                labels=incident.labels,
                metadata=incident.extra_data,
                assigned_to=incident.assigned_to,
                created_by=incident.created_by,
                created_at=incident.created_at,
                updated_at=incident.updated_at,
                resolved_at=incident.resolved_at,
                closed_at=incident.closed_at,
                slack_thread_ts=incident.slack_thread_ts,
                pagerduty_incident_id=incident.pagerduty_incident_id,
                alert_ids=[alert.id for alert in incident.alerts],
                runbook_execution_ids=[exec.id for exec in incident.runbook_executions],
            )
        )
    return responses


@router.get("/{incident_id}", response_model=IncidentResponse)
async def get_incident(
    incident_id: UUID,
    session: AsyncSession = Depends(get_db_session),
):
    repo = await _repo(session)
    incident = await repo.get(incident_id)
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")
    return IncidentResponse(
        id=incident.id,
        fingerprint=incident.fingerprint,
        title=incident.title,
        description=incident.description,
        category=incident.category,
        severity=incident.severity,
        status=incident.status,
        labels=incident.labels,
        metadata=incident.extra_data,
        assigned_to=incident.assigned_to,
        created_by=incident.created_by,
        created_at=incident.created_at,
        updated_at=incident.updated_at,
        resolved_at=incident.resolved_at,
        closed_at=incident.closed_at,
        slack_thread_ts=incident.slack_thread_ts,
        pagerduty_incident_id=incident.pagerduty_incident_id,
        alert_ids=[alert.id for alert in incident.alerts],
        runbook_execution_ids=[exec.id for exec in incident.runbook_executions],
    )


@router.patch("/{incident_id}", response_model=IncidentResponse)
async def update_incident(
    incident_id: UUID,
    payload: IncidentUpdate,
    session: AsyncSession = Depends(get_db_session),
):
    repo = await _repo(session)
    incident = await repo.get(incident_id)
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(incident, field, value)

    await session.flush()
    return IncidentResponse(
        id=incident.id,
        fingerprint=incident.fingerprint,
        title=incident.title,
        description=incident.description,
        category=incident.category,
        severity=incident.severity,
        status=incident.status,
        labels=incident.labels,
        metadata=incident.extra_data,
        assigned_to=incident.assigned_to,
        created_by=incident.created_by,
        created_at=incident.created_at,
        updated_at=incident.updated_at,
        resolved_at=incident.resolved_at,
        closed_at=incident.closed_at,
        slack_thread_ts=incident.slack_thread_ts,
        pagerduty_incident_id=incident.pagerduty_incident_id,
        alert_ids=[alert.id for alert in incident.alerts],
        runbook_execution_ids=[exec.id for exec in incident.runbook_executions],
    )
