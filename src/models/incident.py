import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import Base
from src.models.enums import IncidentCategory, IncidentSeverity, IncidentStatus


class Incident(Base):
    __tablename__ = "incidents"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    fingerprint: Mapped[str] = mapped_column(String(128), index=True, unique=True)

    title: Mapped[str] = mapped_column(String(255))
    description: Mapped[str] = mapped_column(Text)
    category: Mapped[IncidentCategory] = mapped_column(Enum(IncidentCategory))
    severity: Mapped[IncidentSeverity] = mapped_column(Enum(IncidentSeverity))
    status: Mapped[IncidentStatus] = mapped_column(Enum(IncidentStatus), default=IncidentStatus.new)

    labels: Mapped[dict] = mapped_column(JSONB, default=dict)
    extra_data: Mapped[dict] = mapped_column(JSONB, default=dict)

    assigned_to: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_by: Mapped[str] = mapped_column(String(255), default="system")

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    slack_thread_ts: Mapped[str | None] = mapped_column(String(255), nullable=True)
    pagerduty_incident_id: Mapped[str | None] = mapped_column(String(255), nullable=True)

    alerts = relationship("Alert", back_populates="incident", cascade="all, delete-orphan")
    runbook_executions = relationship(
        "RunbookExecution",
        back_populates="incident",
        cascade="all, delete-orphan",
    )
    ml_insights = relationship(
        "MLInsight",
        back_populates="incident",
        cascade="all, delete-orphan",
    )
    copilot_conversations = relationship(
        "CopilotConversation",
        back_populates="incident",
        cascade="all, delete-orphan",
    )


class Alert(Base):
    __tablename__ = "alerts"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    incident_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("incidents.id", ondelete="SET NULL"),
        nullable=True,
    )

    source: Mapped[str] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(32))
    severity: Mapped[str] = mapped_column(String(32))
    message: Mapped[str] = mapped_column(Text)
    fingerprint: Mapped[str] = mapped_column(String(128), index=True)

    labels: Mapped[dict] = mapped_column(JSONB, default=dict)
    annotations: Mapped[dict] = mapped_column(JSONB, default=dict)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    incident = relationship("Incident", back_populates="alerts")
