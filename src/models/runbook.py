import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import Base
from src.models.enums import ExecutionStatus


class Runbook(Base):
    __tablename__ = "runbooks"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255))
    description: Mapped[str] = mapped_column(String(2048))
    version: Mapped[str] = mapped_column(String(32), default="1.0.0")

    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    trigger_conditions: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    steps: Mapped[list] = mapped_column(JSONB, default=list)
    rollback_steps: Mapped[list | None] = mapped_column(JSONB, nullable=True)

    created_by: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    tags: Mapped[list] = mapped_column(JSONB, default=list)

    auto_execute: Mapped[bool] = mapped_column(Boolean, default=False)
    max_concurrent_executions: Mapped[int] = mapped_column(Integer, default=1)

    executions = relationship("RunbookExecution", back_populates="runbook", cascade="all, delete-orphan")


class RunbookExecution(Base):
    __tablename__ = "runbook_executions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    runbook_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("runbooks.id", ondelete="CASCADE"))
    runbook_version: Mapped[str] = mapped_column(String(32))
    incident_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("incidents.id", ondelete="SET NULL"))

    status: Mapped[ExecutionStatus] = mapped_column(Enum(ExecutionStatus), default=ExecutionStatus.pending)
    started_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    step_results: Mapped[list] = mapped_column(JSONB, default=list)
    execution_context: Mapped[dict] = mapped_column(JSONB, default=dict)
    logs: Mapped[list] = mapped_column(JSONB, default=list)

    total_steps: Mapped[int] = mapped_column(Integer, default=0)
    successful_steps: Mapped[int] = mapped_column(Integer, default=0)
    failed_steps: Mapped[int] = mapped_column(Integer, default=0)
    skipped_steps: Mapped[int] = mapped_column(Integer, default=0)

    runbook = relationship("Runbook", back_populates="executions")
    incident = relationship("Incident", back_populates="runbook_executions")
