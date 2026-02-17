from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Dict

from src.services.runbook.executors.base import StepExecutor
from src.config.integrations_config import load_integrations_config
from src.services.integrations.loki import LokiIntegration


class QueryLogsExecutor(StepExecutor):
    async def execute(self, step: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        params = step.get("params", {})
        query = params.get("query")
        if not query:
            raise ValueError("query_logs step requires params.query")
        config = load_integrations_config()
        loki_cfg = config.get("observability", {}).get("loki", {})
        if not loki_cfg.get("enabled", False):
            raise ValueError("Loki integration is disabled.")

        integration = LokiIntegration({"url": loki_cfg.get("url")})
        limit = params.get("limit", loki_cfg.get("queries", {}).get("default_limit", 1000))
        time_range = params.get("time_range")
        range_seconds = params.get("range_seconds", 900)
        start = None
        end = None
        if time_range:
            # Basic parsing like "15m", "1h", "30s"
            unit = time_range[-1]
            value = int(time_range[:-1])
            seconds = value * {"s": 1, "m": 60, "h": 3600}.get(unit, 60)
            end = datetime.now(timezone.utc)
            start = end - timedelta(seconds=seconds)
        result = await integration.query(
            query=query,
            limit=limit,
            start=start,
            end=end,
            range_seconds=range_seconds,
        )
        return {
            "step_id": step.get("id"),
            "step_name": step.get("name"),
            "status": "success",
            "output": {"query": query, "logs": result},
        }
