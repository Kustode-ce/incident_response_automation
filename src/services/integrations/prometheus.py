from __future__ import annotations

from typing import Any, Dict

import httpx

from src.services.integrations.base import BaseIntegration


class PrometheusIntegration(BaseIntegration):
    async def query(self, query: str) -> Dict[str, Any]:
        base_url = self.config.get("base_url") or self.config.get("url")
        if not base_url:
            raise ValueError("Prometheus base_url not configured.")

        async with httpx.AsyncClient() as client:
            resp = await client.get(f"{base_url}/api/v1/query", params={"query": query})
        return resp.json()
