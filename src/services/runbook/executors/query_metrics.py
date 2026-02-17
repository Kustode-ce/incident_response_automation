from __future__ import annotations

from typing import Any, Dict

from src.services.runbook.executors.base import StepExecutor
from src.config.integrations_config import load_integrations_config
from src.services.integrations.prometheus import PrometheusIntegration


class QueryMetricsExecutor(StepExecutor):
    async def execute(self, step: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        params = step.get("params", {})
        query = params.get("query")
        if not query:
            raise ValueError("query_metrics step requires params.query")
        config = load_integrations_config()
        prom_cfg = config.get("observability", {}).get("prometheus", {})
        if not prom_cfg.get("enabled", False):
            raise ValueError("Prometheus integration is disabled.")
        integration = PrometheusIntegration({"url": prom_cfg.get("url")})
        result = await integration.query(query=query)
        return {
            "step_id": step.get("id"),
            "step_name": step.get("name"),
            "status": "success",
            "output": {"query": query, "value": result},
        }
