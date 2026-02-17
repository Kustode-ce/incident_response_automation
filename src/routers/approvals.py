from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.schemas import ApprovalAction, ApprovalRequestResponse
from src.repositories import ApprovalRepository
from src.services.approval_service import ApprovalService
from src.services.runbook_service import RunbookService
from src.utils.database import get_db_session

router = APIRouter(prefix="/approvals", tags=["Approvals"])


async def _repo(session: AsyncSession) -> ApprovalRepository:
    return ApprovalRepository(session)


@router.get("/", response_model=List[ApprovalRequestResponse])
async def list_approvals(
    limit: int = 100,
    offset: int = 0,
    session: AsyncSession = Depends(get_db_session),
):
    repo = await _repo(session)
    approvals = await repo.list(limit=limit, offset=offset)
    return [
        ApprovalRequestResponse(
            id=approval.id,
            runbook_execution_id=approval.runbook_execution_id,
            step_id=approval.step_id,
            step_type=approval.step_type,
            status=approval.status,
            requested_by=approval.requested_by,
            approved_by=approval.approved_by,
            reason=approval.reason,
            metadata=approval.extra_data,
            created_at=approval.created_at,
            resolved_at=approval.resolved_at,
        )
        for approval in approvals
    ]


@router.post("/{approval_id}/approve", response_model=ApprovalRequestResponse)
async def approve_request(
    approval_id: UUID,
    payload: ApprovalAction,
    session: AsyncSession = Depends(get_db_session),
):
    repo = await _repo(session)
    approval = await repo.get(approval_id)
    if not approval:
        raise HTTPException(status_code=404, detail="Approval request not found")
    service = ApprovalService(session)
    approval = await service.approve(approval, payload.actor, payload.reason)
    runbook_service = RunbookService(session)
    await runbook_service.resume_execution(str(approval.runbook_execution_id))
    return ApprovalRequestResponse(
        id=approval.id,
        runbook_execution_id=approval.runbook_execution_id,
        step_id=approval.step_id,
        step_type=approval.step_type,
        status=approval.status,
        requested_by=approval.requested_by,
        approved_by=approval.approved_by,
        reason=approval.reason,
        metadata=approval.metadata,
        created_at=approval.created_at,
        resolved_at=approval.resolved_at,
    )


@router.post("/{approval_id}/reject", response_model=ApprovalRequestResponse)
async def reject_request(
    approval_id: UUID,
    payload: ApprovalAction,
    session: AsyncSession = Depends(get_db_session),
):
    repo = await _repo(session)
    approval = await repo.get(approval_id)
    if not approval:
        raise HTTPException(status_code=404, detail="Approval request not found")
    service = ApprovalService(session)
    approval = await service.reject(approval, payload.actor, payload.reason)
    return ApprovalRequestResponse(
        id=approval.id,
        runbook_execution_id=approval.runbook_execution_id,
        step_id=approval.step_id,
        step_type=approval.step_type,
        status=approval.status,
        requested_by=approval.requested_by,
        approved_by=approval.approved_by,
        reason=approval.reason,
        metadata=approval.metadata,
        created_at=approval.created_at,
        resolved_at=approval.resolved_at,
    )
