from __future__ import annotations

from typing import Any, Dict

from src.services.runbook.executors.base import StepExecutor


class ManualApprovalExecutor(StepExecutor):
    async def execute(self, step: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        # Placeholder: actual implementation will request approval via integrations.
        return {
            "step_id": step.get("id"),
            "step_name": step.get("name"),
            "status": "waiting_approval",
            "output": {"requires_approval": True},
        }
