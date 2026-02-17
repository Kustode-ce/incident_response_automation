from datetime import datetime
from typing import Any, Dict, Optional
from uuid import UUID

from src.models.schemas.base import APIModel


class IntegrationCreate(APIModel):
    type: str
    name: str
    enabled: bool = True
    config: Dict[str, Any] = {}
    credentials: Dict[str, Any] = {}


class IntegrationUpdate(APIModel):
    name: Optional[str] = None
    enabled: Optional[bool] = None
    config: Optional[Dict[str, Any]] = None
    credentials: Optional[Dict[str, Any]] = None


class IntegrationResponse(APIModel):
    id: UUID
    type: str
    name: str
    enabled: bool
    config: Dict[str, Any]
    credentials: Dict[str, Any]
    created_at: datetime
    updated_at: datetime
