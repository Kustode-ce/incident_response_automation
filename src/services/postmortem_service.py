from __future__ import annotations

from typing import List
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.models import Incident
from src.repositories import (
    AlertRepository,
    AuditLogRepository,
    IncidentRepository,
    MLInsightRepository,
    RunbookExecutionRepository,
)


class PostmortemService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.incidents = IncidentRepository(session)
        self.alerts = AlertRepository(session)
        self.executions = RunbookExecutionRepository(session)
        self.ml_insights = MLInsightRepository(session)
        self.audit_logs = AuditLogRepository(session)

    async def generate(self, incident_id: UUID) -> str:
        incident = await self.incidents.get(incident_id)
        if not incident:
            raise ValueError("Incident not found")

        alerts = [alert for alert in await self.alerts.list(limit=200, offset=0) if alert.incident_id == incident_id]
        executions = [
            exec
            for exec in await self.executions.list(limit=200, offset=0)
            if exec.incident_id == incident_id
        ]
        insights = [
            insight
            for insight in await self.ml_insights.list(limit=200, offset=0)
            if insight.incident_id == incident_id
        ]
        audit_logs = [
            log
            for log in await self.audit_logs.list(limit=500, offset=0)
            if log.incident_id == incident_id
        ]

        timeline: List[str] = []
        for alert in alerts:
            timeline.append(f"- {alert.created_at.isoformat()} alert: {alert.message}")
        for exec in executions:
            timeline.append(f"- {exec.started_at.isoformat()} runbook executed: {exec.runbook_id}")
        for log in audit_logs:
            timeline.append(f"- {log.created_at.isoformat()} audit: {log.action}")

        action_items: List[str] = []
        if incident.severity.value in {"high", "critical"}:
            action_items.append("Review alert thresholds for early detection.")
            action_items.append("Add automated rollback or mitigation step.")
        if not executions:
            action_items.append("Create a mitigation runbook for this incident class.")

        insight_notes = "\n".join(f"- {insight.task_type}: {insight.result}" for insight in insights)
        timeline_text = "\n".join(sorted(timeline)) if timeline else "- No timeline events recorded."
        action_items_text = "\n".join(f"- {item}" for item in action_items) if action_items else "- No action items."

        return f"""# Postmortem: {incident.title}

## Summary
- Incident ID: {incident.id}
- Severity: {incident.severity}
- Status: {incident.status}
- Category: {incident.category}

## Timeline
{timeline_text}

## ML Insights
{insight_notes if insight_notes else "- No ML insights recorded."}

## Action Items
{action_items_text}
"""
