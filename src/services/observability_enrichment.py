"""Observability enrichment service.

Queries Prometheus and Loki from the backend observability stack
to gather context for a newly created incident. The gathered context
is stored in ``incident.extra_data["enrichment"]``.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from src.services.integrations.loki import LokiIntegration
from src.services.integrations.prometheus import PrometheusIntegration
from src.settings import settings

logger = logging.getLogger(__name__)


def _prom_client() -> PrometheusIntegration:
    return PrometheusIntegration(config={"base_url": settings.prometheus_url})


def _loki_client() -> LokiIntegration:
    return LokiIntegration(config={"base_url": settings.loki_url})


async def enrich_incident(incident) -> dict[str, Any]:
    """Gather enrichment data from the observability stack.

    Args:
        incident: An ``Incident`` ORM instance (or anything with
            ``extra_data`` and ``labels`` dicts).

    Returns:
        A dict of enrichment data to merge into ``incident.extra_data``.
    """
    service = (
        (incident.extra_data or {}).get("service")
        or (incident.labels or {}).get("service", "")
    )

    enrichment: dict[str, Any] = {"source_service": service}

    if not service:
        logger.info("No service label on incident %s — skipping enrichment", incident.id)
        return enrichment

    prom = _prom_client()
    loki = _loki_client()

    error_rate_task = prom.query_error_rate(service)
    p95_task = prom.query_latency_p95(service)
    rps_task = prom.query_request_rate(service)
    error_logs_task = loki.query_error_logs(service, window_minutes=15, limit=30)

    error_rate, p95, rps, error_logs = await asyncio.gather(
        error_rate_task, p95_task, rps_task, error_logs_task,
        return_exceptions=True,
    )

    if not isinstance(error_rate, BaseException):
        enrichment["error_rate_5m"] = error_rate
    if not isinstance(p95, BaseException):
        enrichment["latency_p95_5m"] = p95
    if not isinstance(rps, BaseException):
        enrichment["request_rate_5m"] = rps
    if not isinstance(error_logs, BaseException):
        enrichment["recent_error_logs"] = error_logs[:20]

    logger.info(
        "Enrichment for incident %s (service=%s): error_rate=%s, p95=%s, rps=%s, error_log_lines=%d",
        incident.id, service,
        enrichment.get("error_rate_5m"),
        enrichment.get("latency_p95_5m"),
        enrichment.get("request_rate_5m"),
        len(enrichment.get("recent_error_logs", [])),
    )
    return enrichment
