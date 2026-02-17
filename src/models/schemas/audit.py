from datetime import datetime
from typing import Any, Dict, Optional
from uuid import UUID

from src.models.schemas.base import APIModel


class AuditLogResponse(APIModel):
    id: UUID
    incident_id: Optional[UUID]
    runbook_execution_id: Optional[UUID]
    action: str
    actor: str
    status: str
    details: Dict[str, Any]
    created_at: datetime
