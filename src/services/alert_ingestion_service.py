"""Alert ingestion service.

Normalizes incoming alerts from AlertManager (and other sources),
deduplicates via fingerprinting, and creates or updates incidents.
"""

from __future__ import annotations

import hashlib
import logging
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models import Alert, Incident
from src.models.enums import AlertStatus, IncidentCategory, IncidentSeverity, IncidentStatus
from src.repositories import AlertRepository, IncidentRepository

logger = logging.getLogger(__name__)

SEVERITY_MAP: dict[str, IncidentSeverity] = {
    "critical": IncidentSeverity.critical,
    "high": IncidentSeverity.high,
    "warning": IncidentSeverity.medium,
    "medium": IncidentSeverity.medium,
    "low": IncidentSeverity.low,
    "info": IncidentSeverity.info,
}

CATEGORY_MAP: dict[str, IncidentCategory] = {
    "database": IncidentCategory.database,
    "db": IncidentCategory.database,
    "network": IncidentCategory.network,
    "security": IncidentCategory.security,
    "infrastructure": IncidentCategory.infrastructure,
    "infra": IncidentCategory.infrastructure,
    "application": IncidentCategory.application,
    "app": IncidentCategory.application,
}


def compute_fingerprint(source: str, alertname: str, labels: dict[str, str]) -> str:
    """Deterministic fingerprint for deduplication.

    Uses source + alertname + sorted label key-value pairs so the same
    alert firing repeatedly produces the same fingerprint.
    """
    stable_labels = sorted(
        (k, v) for k, v in labels.items()
        if k not in ("alertname", "severity")
    )
    raw = f"{source}:{alertname}:{stable_labels}"
    return hashlib.sha256(raw.encode()).hexdigest()[:32]


def map_severity(labels: dict[str, str]) -> IncidentSeverity:
    raw = labels.get("severity", "medium").lower()
    return SEVERITY_MAP.get(raw, IncidentSeverity.medium)


def map_category(labels: dict[str, str]) -> IncidentCategory:
    for field in ("category", "job", "service_type"):
        val = labels.get(field, "").lower()
        if val in CATEGORY_MAP:
            return CATEGORY_MAP[val]

    service = labels.get("service", "")
    if "db" in service or "postgres" in service or "redis" in service:
        return IncidentCategory.database
    if "nginx" in service or "network" in service:
        return IncidentCategory.network

    return IncidentCategory.application


class AlertIngestionService:
    """Ingests alerts from AlertManager and creates/links incidents."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.incident_repo = IncidentRepository(session)
        self.alert_repo = AlertRepository(session)

    async def ingest_alertmanager(self, payload: dict[str, Any]) -> list[dict[str, Any]]:
        """Process an AlertManager webhook payload.

        Returns a list of dicts describing what happened for each alert
        (created, deduplicated, resolved).
        """
        group_status = payload.get("status", "firing")
        alerts = payload.get("alerts", [])
        results: list[dict[str, Any]] = []

        for raw_alert in alerts:
            try:
                result = await self._process_single_alert(raw_alert, group_status)
                results.append(result)
            except Exception:
                logger.exception("Failed to process alert: %s", raw_alert.get("labels", {}))
                results.append({"status": "error", "alert": raw_alert.get("labels", {})})

        return results

    async def _process_single_alert(
        self, raw_alert: dict[str, Any], group_status: str,
    ) -> dict[str, Any]:
        labels: dict[str, str] = raw_alert.get("labels", {})
        annotations: dict[str, str] = raw_alert.get("annotations", {})
        alert_status = raw_alert.get("status", group_status)
        alertname = labels.get("alertname", "unknown")

        fingerprint = compute_fingerprint("alertmanager", alertname, labels)
        severity = map_severity(labels)
        category = map_category(labels)

        title = annotations.get("summary", alertname)
        description = annotations.get("description", f"Alert {alertname} is {alert_status}")

        alert_record = Alert(
            source="alertmanager",
            status=alert_status,
            severity=severity.value,
            message=description,
            fingerprint=fingerprint,
            labels=labels,
            annotations=annotations,
        )

        if alert_status == AlertStatus.resolved.value:
            return await self._handle_resolved(alert_record, fingerprint)

        return await self._find_or_create_incident(
            alert_record, fingerprint, title, description, severity, category, labels,
        )

    async def _find_or_create_incident(
        self,
        alert: Alert,
        fingerprint: str,
        title: str,
        description: str,
        severity: IncidentSeverity,
        category: IncidentCategory,
        labels: dict[str, str],
    ) -> dict[str, Any]:
        """Find existing open incident by fingerprint, or create a new one."""
        result = await self.session.execute(
            select(Incident).where(
                Incident.fingerprint == fingerprint,
                Incident.status.notin_([IncidentStatus.resolved, IncidentStatus.closed]),
            )
        )
        existing = result.scalar_one_or_none()

        if existing:
            alert.incident_id = existing.id
            await self.alert_repo.create(alert)
            logger.info("Deduplicated alert into incident %s (%s)", existing.id, fingerprint)
            return {
                "status": "deduplicated",
                "incident_id": str(existing.id),
                "fingerprint": fingerprint,
            }

        incident = Incident(
            fingerprint=fingerprint,
            title=title,
            description=description,
            category=category,
            severity=severity,
            status=IncidentStatus.new,
            labels={k: v for k, v in labels.items() if k != "alertname"},
            extra_data={
                "source": "alertmanager",
                "alertname": labels.get("alertname", ""),
                "service": labels.get("service", ""),
            },
            created_by="alertmanager",
        )
        await self.incident_repo.create(incident)

        alert.incident_id = incident.id
        await self.alert_repo.create(alert)

        logger.info("Created incident %s from alert %s", incident.id, fingerprint)
        return {
            "status": "created",
            "incident_id": str(incident.id),
            "fingerprint": fingerprint,
            "severity": severity.value,
        }

    async def _handle_resolved(
        self, alert: Alert, fingerprint: str,
    ) -> dict[str, Any]:
        """When a resolved alert arrives, transition the incident to monitoring."""
        result = await self.session.execute(
            select(Incident).where(
                Incident.fingerprint == fingerprint,
                Incident.status.notin_([IncidentStatus.resolved, IncidentStatus.closed]),
            )
        )
        incident = result.scalar_one_or_none()

        if not incident:
            logger.info("Resolved alert for fingerprint %s but no open incident found", fingerprint)
            return {"status": "ignored", "reason": "no_open_incident", "fingerprint": fingerprint}

        alert.incident_id = incident.id
        await self.alert_repo.create(alert)

        incident.status = IncidentStatus.monitoring
        incident.resolved_at = datetime.now(timezone.utc)
        await self.session.flush()

        logger.info("Incident %s moved to monitoring (resolved alert)", incident.id)
        return {
            "status": "resolved",
            "incident_id": str(incident.id),
            "fingerprint": fingerprint,
        }
