from datetime import datetime
from typing import Any, Dict, Optional
from uuid import UUID

from src.models.enums import MLTaskType
from src.models.schemas.base import APIModel


class MLInsightCreate(APIModel):
    incident_id: Optional[UUID] = None
    task_type: MLTaskType
    model_name: str
    model_version: str
    provider: str
    result: Dict[str, Any]
    confidence: Optional[float] = None
    latency_ms: Optional[float] = None
    tokens_used: Optional[int] = None
    cost_usd: Optional[float] = None
    raw_response: Optional[str] = None


class MLInsightResponse(APIModel):
    id: UUID
    incident_id: Optional[UUID]
    task_type: MLTaskType
    model_name: str
    model_version: str
    provider: str
    result: Dict[str, Any]
    confidence: Optional[float]
    latency_ms: Optional[float]
    tokens_used: Optional[int]
    cost_usd: Optional[float]
    raw_response: Optional[str]
    created_at: datetime
