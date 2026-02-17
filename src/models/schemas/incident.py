from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import Field

from src.models.enums import IncidentCategory, IncidentSeverity, IncidentStatus
from src.models.schemas.base import APIModel


class IncidentCreate(APIModel):
    fingerprint: str
    title: str
    description: str
    category: IncidentCategory
    severity: IncidentSeverity
    status: IncidentStatus = IncidentStatus.new

    labels: Dict[str, str] = Field(default_factory=dict)
    extra_data: Dict[str, Any] = Field(default_factory=dict, alias="metadata")

    assigned_to: Optional[str] = None
    created_by: str = "system"


class IncidentUpdate(APIModel):
    title: Optional[str] = None
    description: Optional[str] = None
    category: Optional[IncidentCategory] = None
    severity: Optional[IncidentSeverity] = None
    status: Optional[IncidentStatus] = None

    labels: Optional[Dict[str, str]] = None
    extra_data: Optional[Dict[str, Any]] = Field(default=None, alias="metadata")

    assigned_to: Optional[str] = None
    resolved_at: Optional[datetime] = None
    closed_at: Optional[datetime] = None


class IncidentResponse(APIModel):
    id: UUID
    fingerprint: str
    title: str
    description: str
    category: IncidentCategory
    severity: IncidentSeverity
    status: IncidentStatus

    labels: Dict[str, str] = Field(default_factory=dict)
    metadata: Dict[str, Any] = Field(default_factory=dict)

    assigned_to: Optional[str] = None
    created_by: str = "system"

    created_at: datetime
    updated_at: datetime
    resolved_at: Optional[datetime] = None
    closed_at: Optional[datetime] = None

    slack_thread_ts: Optional[str] = None
    pagerduty_incident_id: Optional[str] = None

    alert_ids: List[UUID] = Field(default_factory=list)
    runbook_execution_ids: List[UUID] = Field(default_factory=list)
