from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.models import Alert
from src.observability.unified_observability import record_alert_received
from src.models.schemas import AlertCreate, AlertResponse
from src.repositories import AlertRepository
from src.utils.database import get_db_session

router = APIRouter(prefix="/alerts", tags=["Alerts"])


async def _repo(session: AsyncSession) -> AlertRepository:
    return AlertRepository(session)


@router.post("/", response_model=AlertResponse)
async def create_alert(
    payload: AlertCreate,
    session: AsyncSession = Depends(get_db_session),
):
    repo = await _repo(session)
    alert = Alert(**payload.model_dump())
    await repo.create(alert)
    try:
        record_alert_received(source=payload.source, severity=payload.severity)
    except Exception:
        pass
    return AlertResponse(
        id=alert.id,
        incident_id=alert.incident_id,
        source=alert.source,
        status=alert.status,
        severity=alert.severity,
        message=alert.message,
        fingerprint=alert.fingerprint,
        labels=alert.labels,
        annotations=alert.annotations,
        created_at=alert.created_at,
    )


@router.get("/", response_model=List[AlertResponse])
async def list_alerts(
    limit: int = 100,
    offset: int = 0,
    session: AsyncSession = Depends(get_db_session),
):
    repo = await _repo(session)
    alerts = await repo.list(limit=limit, offset=offset)
    return [
        AlertResponse(
            id=alert.id,
            incident_id=alert.incident_id,
            source=alert.source,
            status=alert.status,
            severity=alert.severity,
            message=alert.message,
            fingerprint=alert.fingerprint,
            labels=alert.labels,
            annotations=alert.annotations,
            created_at=alert.created_at,
        )
        for alert in alerts
    ]
