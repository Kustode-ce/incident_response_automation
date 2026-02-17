from datetime import datetime
from typing import Any, Dict, Optional
from uuid import UUID

from pydantic import Field

from src.models.schemas.base import APIModel


class ApprovalRequestCreate(APIModel):
    runbook_execution_id: UUID
    step_id: str
    step_type: str
    requested_by: str = "system"
    reason: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ApprovalAction(APIModel):
    actor: str
    reason: Optional[str] = None


class ApprovalRequestResponse(APIModel):
    id: UUID
    runbook_execution_id: UUID
    step_id: str
    step_type: str
    status: str
    requested_by: str
    approved_by: Optional[str]
    reason: Optional[str]
    metadata: Dict[str, Any]
    created_at: datetime
    resolved_at: Optional[datetime]
