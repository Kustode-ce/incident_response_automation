from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.models import ApprovalRequest
from src.repositories import ApprovalRepository
from src.services.audit_logger import AuditLogger


class ApprovalService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.repo = ApprovalRepository(session)
        self.audit_logger = AuditLogger(session)

    async def request_approval(
        self,
        runbook_execution_id: UUID,
        step_id: str,
        step_type: str,
        requested_by: str = "system",
        reason: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> ApprovalRequest:
        approval = ApprovalRequest(
            runbook_execution_id=runbook_execution_id,
            step_id=step_id,
            step_type=step_type,
            status="pending",
            requested_by=requested_by,
            reason=reason,
            metadata=metadata or {},
        )
        await self.repo.create(approval)
        return approval

    async def approve(self, approval: ApprovalRequest, actor: str, reason: Optional[str] = None) -> ApprovalRequest:
        approval.status = "approved"
        approval.approved_by = actor
        approval.resolved_at = datetime.utcnow()
        if reason:
            approval.reason = reason
        await self.audit_logger.log(
            action="approval_granted",
            actor=actor,
            status="ok",
            details={"approval_id": str(approval.id), "step_id": approval.step_id},
            runbook_execution_id=approval.runbook_execution_id,
        )
        await self.session.flush()
        return approval

    async def reject(self, approval: ApprovalRequest, actor: str, reason: Optional[str] = None) -> ApprovalRequest:
        approval.status = "rejected"
        approval.approved_by = actor
        approval.resolved_at = datetime.utcnow()
        if reason:
            approval.reason = reason
        await self.audit_logger.log(
            action="approval_rejected",
            actor=actor,
            status="ok",
            details={"approval_id": str(approval.id), "step_id": approval.step_id},
            runbook_execution_id=approval.runbook_execution_id,
        )
        await self.session.flush()
        return approval
