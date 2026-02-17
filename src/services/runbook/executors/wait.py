from __future__ import annotations

import asyncio
from typing import Any, Dict

from src.services.runbook.executors.base import StepExecutor


class WaitExecutor(StepExecutor):
    async def execute(self, step: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        duration = step.get("params", {}).get("duration_seconds", 1)
        await asyncio.sleep(duration)
        return {
            "step_id": step.get("id"),
            "step_name": step.get("name"),
            "status": "success",
            "output": {"duration_seconds": duration},
        }
