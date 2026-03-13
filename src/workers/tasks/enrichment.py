"""Celery tasks for post-creation incident enrichment and notification."""

from __future__ import annotations

import asyncio
import logging
from uuid import UUID

import httpx

from src.workers.celery_app import celery_app

logger = logging.getLogger(__name__)


def _run_async(coro):
    """Run an async coroutine from a synchronous Celery worker."""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


@celery_app.task(bind=True, max_retries=2, default_retry_delay=30)
def enrich_and_notify(self, incident_id: str) -> dict:
    """Enrich a newly created incident with observability data, then notify Slack.

    This task is queued automatically when the webhook handler creates an
    incident.  It runs outside the request cycle so the webhook returns fast.
    """
    logger.info("Starting enrichment for incident %s", incident_id)

    try:
        result = _run_async(_enrich_and_notify_async(incident_id))
        return result
    except Exception as exc:
        logger.exception("Enrichment failed for incident %s", incident_id)
        raise self.retry(exc=exc)


async def _enrich_and_notify_async(incident_id: str) -> dict:
    from src.utils.database import init_engine, get_db_session_context
    from src.repositories import IncidentRepository
    from src.services.observability_enrichment import enrich_incident
    from src.settings import settings

    init_engine()

    async with get_db_session_context() as session:
        repo = IncidentRepository(session)
        incident = await repo.get(UUID(incident_id))

        if not incident:
            logger.warning("Incident %s not found — skipping enrichment", incident_id)
            return {"status": "not_found"}

        if settings.enable_observability_enrichment:
            enrichment = await enrich_incident(incident)
            extra = dict(incident.extra_data or {})
            extra["enrichment"] = enrichment
            incident.extra_data = extra
            await session.flush()
            logger.info("Stored enrichment for incident %s", incident_id)

        if settings.enable_slack_notifications and settings.slack_webhook_url:
            await _post_slack_notification(incident, settings)

    return {"status": "enriched", "incident_id": incident_id}


async def _post_slack_notification(incident, settings) -> None:
    """Post a Slack message about a new incident."""
    severity_emoji = {
        "critical": ":rotating_light:",
        "high": ":warning:",
        "medium": ":bell:",
        "low": ":information_source:",
        "info": ":speech_balloon:",
    }
    emoji = severity_emoji.get(incident.severity.value if hasattr(incident.severity, "value") else str(incident.severity), ":bell:")
    enrichment = (incident.extra_data or {}).get("enrichment", {})

    blocks = [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": f"{emoji} New Incident: {incident.title}",
            },
        },
        {
            "type": "section",
            "fields": [
                {"type": "mrkdwn", "text": f"*Severity:* {incident.severity.value if hasattr(incident.severity, 'value') else incident.severity}"},
                {"type": "mrkdwn", "text": f"*Category:* {incident.category.value if hasattr(incident.category, 'value') else incident.category}"},
                {"type": "mrkdwn", "text": f"*Status:* {incident.status.value if hasattr(incident.status, 'value') else incident.status}"},
                {"type": "mrkdwn", "text": f"*Service:* {enrichment.get('source_service', 'unknown')}"},
            ],
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*Description:*\n{incident.description[:500]}",
            },
        },
    ]

    if enrichment.get("error_rate_5m") is not None or enrichment.get("latency_p95_5m") is not None:
        metrics_parts = []
        if enrichment.get("error_rate_5m") is not None:
            metrics_parts.append(f"Error Rate: {enrichment['error_rate_5m']:.2%}")
        if enrichment.get("latency_p95_5m") is not None:
            metrics_parts.append(f"p95 Latency: {enrichment['latency_p95_5m']:.3f}s")
        if enrichment.get("request_rate_5m") is not None:
            metrics_parts.append(f"RPS: {enrichment['request_rate_5m']:.1f}")

        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*Observability Snapshot:*\n" + " | ".join(metrics_parts),
            },
        })

    error_logs = enrichment.get("recent_error_logs", [])
    if error_logs:
        log_preview = "\n".join(error_logs[:5])
        if len(log_preview) > 2900:
            log_preview = log_preview[:2900] + "\n..."
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*Recent Errors (Loki):*\n```{log_preview}```",
            },
        })

    payload = {
        "channel": settings.slack_incidents_channel,
        "text": f"{emoji} New Incident: {incident.title}",
        "blocks": blocks,
    }

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(settings.slack_webhook_url, json=payload)
            resp.raise_for_status()
        logger.info("Slack notification sent for incident %s", incident.id)
    except Exception:
        logger.warning("Failed to send Slack notification for incident %s", incident.id)
