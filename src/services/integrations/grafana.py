from __future__ import annotations

from typing import Any, Dict

import httpx

from src.services.integrations.base import BaseIntegration


class GrafanaIntegration(BaseIntegration):
    async def get_dashboard(self, dashboard_uid: str) -> Dict[str, Any]:
        base_url = self.config.get("base_url")
        api_key = self.config.get("api_key")
        if not base_url or not api_key:
            raise ValueError("Grafana base_url or api_key not configured.")

        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{base_url}/api/dashboards/uid/{dashboard_uid}",
                headers={"Authorization": f"Bearer {api_key}"},
            )
        return resp.json()
