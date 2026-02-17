from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

import httpx

from src.services.integrations.base import BaseIntegration


class LokiIntegration(BaseIntegration):
    async def query(
        self,
        query: str,
        limit: int = 100,
        start: Optional[datetime] = None,
        end: Optional[datetime] = None,
        range_seconds: int = 900,
    ) -> Dict[str, Any]:
        base_url = self.config.get("base_url") or self.config.get("url")
        if not base_url:
            raise ValueError("Loki base_url not configured.")

        now = datetime.now(timezone.utc)
        end_time = end or now
        start_time = start or (end_time - timedelta(seconds=range_seconds))
        params = {
            "query": query,
            "limit": limit,
            "start": int(start_time.timestamp() * 1_000_000_000),
            "end": int(end_time.timestamp() * 1_000_000_000),
        }
        async with httpx.AsyncClient() as client:
            resp = await client.get(f"{base_url}/loki/api/v1/query_range", params=params)
        return resp.json()
