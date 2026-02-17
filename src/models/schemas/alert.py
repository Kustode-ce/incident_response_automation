from datetime import datetime
from typing import Any, Dict, Optional
from uuid import UUID

from pydantic import Field

from src.models.schemas.base import APIModel


class AlertCreate(APIModel):
    source: str
    status: str
    severity: str
    message: str
    fingerprint: str
    labels: Dict[str, str] = Field(default_factory=dict)
    annotations: Dict[str, Any] = Field(default_factory=dict)
    incident_id: Optional[UUID] = None


class AlertResponse(APIModel):
    id: UUID
    incident_id: Optional[UUID]
    source: str
    status: str
    severity: str
    message: str
    fingerprint: str
    labels: Dict[str, str]
    annotations: Dict[str, Any]
    created_at: datetime
