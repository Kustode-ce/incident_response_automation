from __future__ import annotations

import logging
from typing import Any, Dict

import httpx

from src.services.integrations.base import BaseIntegration

logger = logging.getLogger(__name__)


class PrometheusIntegration(BaseIntegration):
    @property
    def base_url(self) -> str:
        url = self.config.get("base_url") or self.config.get("url")
        if not url:
            raise ValueError("Prometheus base_url not configured.")
        return url.rstrip("/")

    async def query(self, query: str) -> Dict[str, Any]:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(
                f"{self.base_url}/api/v1/query",
                params={"query": query},
            )
        return resp.json()

    async def query_range(
        self, query: str, start: str, end: str, step: str = "60s",
    ) -> Dict[str, Any]:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(
                f"{self.base_url}/api/v1/query_range",
                params={"query": query, "start": start, "end": end, "step": step},
            )
        return resp.json()

    async def query_error_rate(self, service: str, window: str = "5m") -> float | None:
        """Return the 5xx error rate for a service over the given window."""
        q = (
            f'sum(rate(http_requests_total{{service="{service}",status=~"5.."}}[{window}]))'
            f' / sum(rate(http_requests_total{{service="{service}"}}[{window}]))'
        )
        try:
            result = await self.query(q)
            values = result.get("data", {}).get("result", [])
            if values:
                return float(values[0]["value"][1])
        except Exception:
            logger.warning("Failed to query error rate for %s", service)
        return None

    async def query_latency_p95(self, service: str, window: str = "5m") -> float | None:
        """Return p95 request latency in seconds for a service."""
        q = (
            f'histogram_quantile(0.95,'
            f' sum(rate(http_request_duration_seconds_bucket{{service="{service}"}}[{window}])) by (le))'
        )
        try:
            result = await self.query(q)
            values = result.get("data", {}).get("result", [])
            if values:
                return float(values[0]["value"][1])
        except Exception:
            logger.warning("Failed to query p95 latency for %s", service)
        return None

    async def query_request_rate(self, service: str, window: str = "5m") -> float | None:
        """Return request rate (req/s) for a service."""
        q = f'sum(rate(http_requests_total{{service="{service}"}}[{window}]))'
        try:
            result = await self.query(q)
            values = result.get("data", {}).get("result", [])
            if values:
                return float(values[0]["value"][1])
        except Exception:
            logger.warning("Failed to query request rate for %s", service)
        return None
