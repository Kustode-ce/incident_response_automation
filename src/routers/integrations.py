from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from src.models import Integration
from src.models.schemas import IntegrationCreate, IntegrationResponse, IntegrationUpdate
from src.repositories import IntegrationRepository
from src.utils.database import get_db_session

router = APIRouter(prefix="/integrations", tags=["Integrations"])


async def _repo(session: AsyncSession) -> IntegrationRepository:
    return IntegrationRepository(session)


@router.post("/", response_model=IntegrationResponse)
async def create_integration(
    payload: IntegrationCreate,
    session: AsyncSession = Depends(get_db_session),
):
    repo = await _repo(session)
    integration = Integration(**payload.model_dump())
    await repo.create(integration)
    return IntegrationResponse(
        id=integration.id,
        type=integration.type,
        name=integration.name,
        enabled=integration.enabled,
        config=integration.config,
        credentials=integration.credentials,
        created_at=integration.created_at,
        updated_at=integration.updated_at,
    )


@router.get("/", response_model=List[IntegrationResponse])
async def list_integrations(
    limit: int = 100,
    offset: int = 0,
    session: AsyncSession = Depends(get_db_session),
):
    repo = await _repo(session)
    integrations = await repo.list(limit=limit, offset=offset)
    return [
        IntegrationResponse(
            id=integration.id,
            type=integration.type,
            name=integration.name,
            enabled=integration.enabled,
            config=integration.config,
            credentials=integration.credentials,
            created_at=integration.created_at,
            updated_at=integration.updated_at,
        )
        for integration in integrations
    ]


@router.get("/{integration_id}", response_model=IntegrationResponse)
async def get_integration(
    integration_id: UUID,
    session: AsyncSession = Depends(get_db_session),
):
    repo = await _repo(session)
    integration = await repo.get(integration_id)
    if not integration:
        raise HTTPException(status_code=404, detail="Integration not found")
    return IntegrationResponse(
        id=integration.id,
        type=integration.type,
        name=integration.name,
        enabled=integration.enabled,
        config=integration.config,
        credentials=integration.credentials,
        created_at=integration.created_at,
        updated_at=integration.updated_at,
    )


@router.patch("/{integration_id}", response_model=IntegrationResponse)
async def update_integration(
    integration_id: UUID,
    payload: IntegrationUpdate,
    session: AsyncSession = Depends(get_db_session),
):
    repo = await _repo(session)
    integration = await repo.get(integration_id)
    if not integration:
        raise HTTPException(status_code=404, detail="Integration not found")

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(integration, field, value)

    await session.flush()
    return IntegrationResponse(
        id=integration.id,
        type=integration.type,
        name=integration.name,
        enabled=integration.enabled,
        config=integration.config,
        credentials=integration.credentials,
        created_at=integration.created_at,
        updated_at=integration.updated_at,
    )
