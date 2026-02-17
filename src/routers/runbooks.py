from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from src.models import Runbook
from src.models.schemas import RunbookCreate, RunbookExecuteRequest, RunbookExecutionResponse, RunbookResponse, RunbookUpdate
from src.repositories import RunbookRepository
from src.services.runbook_service import RunbookService
from src.utils.database import get_db_session

router = APIRouter(prefix="/runbooks", tags=["Runbooks"])


async def _repo(session: AsyncSession) -> RunbookRepository:
    return RunbookRepository(session)


@router.post("/", response_model=RunbookResponse)
async def create_runbook(
    payload: RunbookCreate,
    session: AsyncSession = Depends(get_db_session),
):
    repo = await _repo(session)
    runbook = Runbook(**payload.model_dump())
    await repo.create(runbook)
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


@router.get("/", response_model=List[RunbookResponse])
async def list_runbooks(
    limit: int = 100,
    offset: int = 0,
    session: AsyncSession = Depends(get_db_session),
):
    repo = await _repo(session)
    runbooks = await repo.list(limit=limit, offset=offset)
    return [
        RunbookResponse(
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
        for runbook in runbooks
    ]


@router.get("/{runbook_id}", response_model=RunbookResponse)
async def get_runbook(
    runbook_id: UUID,
    session: AsyncSession = Depends(get_db_session),
):
    repo = await _repo(session)
    runbook = await repo.get(runbook_id)
    if not runbook:
        raise HTTPException(status_code=404, detail="Runbook not found")
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


@router.patch("/{runbook_id}", response_model=RunbookResponse)
async def update_runbook(
    runbook_id: UUID,
    payload: RunbookUpdate,
    session: AsyncSession = Depends(get_db_session),
):
    repo = await _repo(session)
    runbook = await repo.get(runbook_id)
    if not runbook:
        raise HTTPException(status_code=404, detail="Runbook not found")

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(runbook, field, value)

    await session.flush()
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


@router.post("/{runbook_id}/execute", response_model=RunbookExecutionResponse)
async def execute_runbook(
    runbook_id: UUID,
    payload: RunbookExecuteRequest,
    session: AsyncSession = Depends(get_db_session),
):
    repo = await _repo(session)
    runbook = await repo.get(runbook_id)
    if not runbook:
        raise HTTPException(status_code=404, detail="Runbook not found")

    service = RunbookService(session)
    execution = await service.execute_runbook(
        runbook_id=str(runbook.id),
        runbook_version=runbook.version,
        steps=runbook.steps,
        incident_id=str(payload.incident_id) if payload.incident_id else None,
        execution_context=payload.execution_context,
    )
    return RunbookExecutionResponse(
        id=execution.id,
        runbook_id=runbook_id,
        runbook_version=execution.runbook_version,
        incident_id=execution.incident_id,
        status=execution.status,
        started_at=execution.started_at,
        completed_at=execution.completed_at,
        step_results=execution.step_results,
        execution_context=execution.execution_context,
        logs=execution.logs,
        total_steps=execution.total_steps,
        successful_steps=execution.successful_steps,
        failed_steps=execution.failed_steps,
        skipped_steps=execution.skipped_steps,
    )
