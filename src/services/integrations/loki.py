from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

import httpx

from src.services.integrations.base import BaseIntegration

logger = logging.getLogger(__name__)


class LokiIntegration(BaseIntegration):
    @property
    def base_url(self) -> str:
        url = self.config.get("base_url") or self.config.get("url")
        if not url:
            raise ValueError("Loki base_url not configured.")
        return url.rstrip("/")

    async def query(
        self,
        query: str,
        limit: int = 100,
        start: Optional[datetime] = None,
        end: Optional[datetime] = None,
        range_seconds: int = 900,
    ) -> Dict[str, Any]:
        now = datetime.now(timezone.utc)
        end_time = end or now
        start_time = start or (end_time - timedelta(seconds=range_seconds))
        params = {
            "query": query,
            "limit": limit,
            "start": int(start_time.timestamp() * 1_000_000_000),
            "end": int(end_time.timestamp() * 1_000_000_000),
        }
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(
                f"{self.base_url}/loki/api/v1/query_range",
                params=params,
            )
        return resp.json()

    async def query_error_logs(
        self,
        service: str,
        window_minutes: int = 15,
        limit: int = 50,
    ) -> list[str]:
        """Return recent ERROR-level log lines for a service."""
        logql = f'{{service="{service}"}} |= "ERROR"'
        try:
            result = await self.query(logql, limit=limit, range_seconds=window_minutes * 60)
            streams = result.get("data", {}).get("result", [])
            lines: list[str] = []
            for stream in streams:
                for _ts, line in stream.get("values", []):
                    lines.append(line)
            return lines
        except Exception:
            logger.warning("Failed to query error logs for %s", service)
            return []

    async def query_recent_logs(
        self,
        service: str,
        window_minutes: int = 5,
        limit: int = 100,
    ) -> list[str]:
        """Return recent log lines (all levels) for a service."""
        logql = f'{{service="{service}"}}'
        try:
            result = await self.query(logql, limit=limit, range_seconds=window_minutes * 60)
            streams = result.get("data", {}).get("result", [])
            lines: list[str] = []
            for stream in streams:
                for _ts, line in stream.get("values", []):
                    lines.append(line)
            return lines
        except Exception:
            logger.warning("Failed to query recent logs for %s", service)
            return []
