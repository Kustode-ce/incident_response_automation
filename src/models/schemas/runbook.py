from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import Field

from src.models.enums import ExecutionStatus
from src.models.schemas.base import APIModel


class RunbookCreate(APIModel):
    name: str
    description: str
    version: str = "1.0.0"
    enabled: bool = True
    trigger_conditions: Optional[Dict[str, Any]] = None
    steps: List[Dict[str, Any]]
    rollback_steps: Optional[List[Dict[str, Any]]] = None
    created_by: str
    tags: List[str] = Field(default_factory=list)
    auto_execute: bool = False
    max_concurrent_executions: int = 1


class RunbookUpdate(APIModel):
    name: Optional[str] = None
    description: Optional[str] = None
    version: Optional[str] = None
    enabled: Optional[bool] = None
    trigger_conditions: Optional[Dict[str, Any]] = None
    steps: Optional[List[Dict[str, Any]]] = None
    rollback_steps: Optional[List[Dict[str, Any]]] = None
    tags: Optional[List[str]] = None
    auto_execute: Optional[bool] = None
    max_concurrent_executions: Optional[int] = None


class RunbookResponse(APIModel):
    id: UUID
    name: str
    description: str
    version: str
    enabled: bool
    trigger_conditions: Optional[Dict[str, Any]]
    steps: List[Dict[str, Any]]
    rollback_steps: Optional[List[Dict[str, Any]]]
    created_by: str
    created_at: datetime
    updated_at: datetime
    tags: List[str]
    auto_execute: bool
    max_concurrent_executions: int


class RunbookExecutionResponse(APIModel):
    id: UUID
    runbook_id: UUID
    runbook_version: str
    incident_id: Optional[UUID]
    status: ExecutionStatus
    started_at: datetime
    completed_at: Optional[datetime]
    step_results: List[Dict[str, Any]]
    execution_context: Dict[str, Any]
    logs: List[str]
    total_steps: int
    successful_steps: int
    failed_steps: int
    skipped_steps: int


class RunbookExecuteRequest(APIModel):
    incident_id: Optional[UUID] = None
    execution_context: Dict[str, Any] = Field(default_factory=dict)
