from __future__ import annotations

from typing import Dict

from src.services.runbook.executors.base import StepExecutor
from src.services.runbook.executors.conditional import ConditionalExecutor
from src.services.runbook.executors.http_request import HttpRequestExecutor
from src.services.runbook.executors.kubernetes_action import KubernetesActionExecutor
from src.services.runbook.executors.manual_approval import ManualApprovalExecutor
from src.services.runbook.executors.ml_analysis import MLAnalysisExecutor
from src.services.runbook.executors.notification import NotificationExecutor
from src.services.runbook.executors.parallel import ParallelExecutor
from src.services.runbook.executors.query_logs import QueryLogsExecutor
from src.services.runbook.executors.query_metrics import QueryMetricsExecutor
from src.services.runbook.executors.wait import WaitExecutor


class StepExecutorRegistry:
    def __init__(self):
        self._executors: Dict[str, StepExecutor] = {
            "notification": NotificationExecutor(),
            "http_request": HttpRequestExecutor(),
            "kubernetes_action": KubernetesActionExecutor(),
            "wait": WaitExecutor(),
            "conditional": ConditionalExecutor(self),
            "parallel": ParallelExecutor(self),
            "query_metrics": QueryMetricsExecutor(),
            "query_logs": QueryLogsExecutor(),
            "manual_approval": ManualApprovalExecutor(),
            "ml_analysis": MLAnalysisExecutor(),
        }

    def get(self, step_type: str) -> StepExecutor:
        return self._executors[step_type]

    def supported_types(self) -> list[str]:
        return list(self._executors.keys())
