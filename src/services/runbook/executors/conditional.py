from __future__ import annotations

from typing import Any, Dict, List

from src.services.runbook.executors.base import StepExecutor


class ConditionalExecutor(StepExecutor):
    def __init__(self, registry):
        self.registry = registry

    async def execute(self, step: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        condition = step.get("condition")
        condition_result = bool(condition)

        branch_steps: List[Dict[str, Any]] = step.get("on_success" if condition_result else "on_failure", [])
        branch_results: List[Dict[str, Any]] = []

        for branch_step in branch_steps:
            executor = self.registry.get(branch_step["type"])
            branch_results.append(await executor.execute(branch_step, context))

        return {
            "step_id": step.get("id"),
            "step_name": step.get("name"),
            "status": "success",
            "output": {"condition_result": condition_result, "branch_results": branch_results},
        }
