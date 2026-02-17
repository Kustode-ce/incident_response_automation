from __future__ import annotations

from typing import Any, Dict

import httpx

from src.services.integrations.base import BaseIntegration


class PagerDutyIntegration(BaseIntegration):
    async def create_incident(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        token = self.config.get("api_key")
        if not token:
            raise ValueError("PagerDuty API key not configured.")

        headers = {
            "Authorization": f"Token token={token}",
            "Accept": "application/vnd.pagerduty+json;version=2",
            "Content-Type": "application/json",
        }
        async with httpx.AsyncClient() as client:
            resp = await client.post("https://api.pagerduty.com/incidents", headers=headers, json=payload)
        return resp.json()
