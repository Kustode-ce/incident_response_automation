from __future__ import annotations

from typing import Any, Dict

import httpx

from src.services.runbook.executors.base import StepExecutor


class HttpRequestExecutor(StepExecutor):
    async def execute(self, step: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        params = step.get("params", {})
        method = params.get("method", "GET")
        url = params.get("url")
        if not url:
            raise ValueError("http_request step requires params.url")

        async with httpx.AsyncClient() as client:
            response = await client.request(method, url, json=params.get("body"))

        return {
            "step_id": step.get("id"),
            "step_name": step.get("name"),
            "status": "success" if response.status_code < 400 else "failed",
            "output": {"status_code": response.status_code, "body": response.text},
        }
