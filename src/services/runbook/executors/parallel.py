from __future__ import annotations

import asyncio
from typing import Any, Dict, List

from src.services.runbook.executors.base import StepExecutor


class ParallelExecutor(StepExecutor):
    def __init__(self, registry):
        self.registry = registry

    async def execute(self, step: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        steps: List[Dict[str, Any]] = step.get("steps", [])
        tasks = []
        for child in steps:
            executor = self.registry.get(child["type"])
            tasks.append(executor.execute(child, context))

        results = await asyncio.gather(*tasks)
        return {
            "step_id": step.get("id"),
            "step_name": step.get("name"),
            "status": "success",
            "output": {"results": results},
        }
