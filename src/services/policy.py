from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional

from src.config.integrations_config import load_integrations_config


@dataclass
class PolicyDecision:
    allowed: bool
    requires_approval: bool
    risk_level: str
    reason: str


class PolicyEngine:
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or load_integrations_config()
        self.high_risk_steps = {"kubernetes_action", "http_request", "manual_approval"}
        self.medium_risk_steps = {"query_metrics", "query_logs"}

    def _kubernetes_operation_enabled(self, action: str) -> bool:
        kube = self.config.get("infrastructure", {}).get("kubernetes", {})
        operations = kube.get("operations", {})
        action_config = operations.get(action, {})
        return action_config.get("enabled", False)

    def _ec2_operation_policy(self, operation: str) -> PolicyDecision:
        aws = self.config.get("cloud_providers", {}).get("aws", {})
        ec2 = aws.get("services", {}).get("ec2", {})
        limits = ec2.get("limits", {})
        allowed_ops = set(limits.get("allowed_operations", []))
        approval_ops = set(limits.get("require_approval", []))
        if allowed_ops and operation not in allowed_ops:
            return PolicyDecision(
                allowed=False,
                requires_approval=False,
                risk_level="high",
                reason="EC2 operation not allowed by policy.",
            )
        if operation in approval_ops:
            return PolicyDecision(
                allowed=True,
                requires_approval=True,
                risk_level="high",
                reason="EC2 operation requires approval.",
            )
        return PolicyDecision(
            allowed=True,
            requires_approval=False,
            risk_level="medium",
            reason="EC2 operation allowed.",
        )

    def evaluate(self, step: Dict[str, Any]) -> PolicyDecision:
        step_type = step.get("type")
        params = step.get("params", {})

        if step_type == "kubernetes_action":
            action = params.get("action", "")
            if not self._kubernetes_operation_enabled(action):
                return PolicyDecision(
                    allowed=False,
                    requires_approval=False,
                    risk_level="high",
                    reason="Kubernetes action disabled by policy.",
                )

        if step_type == "ec2_action":
            operation = params.get("operation", "")
            return self._ec2_operation_policy(operation)

        if step_type in self.high_risk_steps:
            if step_type == "http_request" and params.get("method", "GET").upper() in {"POST", "PUT", "PATCH", "DELETE"}:
                return PolicyDecision(
                    allowed=True,
                    requires_approval=True,
                    risk_level="high",
                    reason="Mutating HTTP request requires approval.",
                )
            if step_type == "kubernetes_action":
                return PolicyDecision(
                    allowed=True,
                    requires_approval=True,
                    risk_level="high",
                    reason="Kubernetes mutations require approval.",
                )
            if step_type == "manual_approval":
                return PolicyDecision(
                    allowed=True,
                    requires_approval=True,
                    risk_level="high",
                    reason="Manual approval step pending.",
                )

        if step_type in self.medium_risk_steps:
            return PolicyDecision(
                allowed=True,
                requires_approval=False,
                risk_level="medium",
                reason="Read-only query step.",
            )

        return PolicyDecision(
            allowed=True,
            requires_approval=False,
            risk_level="low",
            reason="Low-risk step.",
        )
