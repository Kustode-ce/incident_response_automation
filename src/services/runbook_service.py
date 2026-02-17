from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List

from sqlalchemy.ext.asyncio import AsyncSession

from src.models import RunbookExecution
from src.models.enums import ExecutionStatus
from src.repositories import RunbookExecutionRepository
from src.services.approval_service import ApprovalService
from src.services.audit_logger import AuditLogger
from src.services.policy import PolicyEngine
from src.observability.unified_observability import record_runbook_execution
from src.services.runbook.registry import StepExecutorRegistry


class RunbookService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.executions = RunbookExecutionRepository(session)
        self.registry = StepExecutorRegistry()
        self.policy_engine = PolicyEngine()
        self.approval_service = ApprovalService(session)
        self.audit_logger = AuditLogger(session)

    def validate_runbook(self, steps: List[Dict[str, Any]]) -> None:
        if not steps:
            raise ValueError("Runbook must contain at least one step.")
        for step in steps:
            if "id" not in step or "type" not in step:
                raise ValueError("Each step must include id and type.")
            if step["type"] not in self.registry.supported_types():
                raise ValueError(f"Unsupported step type: {step['type']}")

    async def execute_runbook(
        self,
        runbook_id: str,
        runbook_version: str,
        steps: List[Dict[str, Any]],
        incident_id: str | None,
        execution_context: Dict[str, Any],
    ) -> RunbookExecution:
        self.validate_runbook(steps)
        if execution_context is None:
            execution_context = {}
        execution_context.setdefault("step_results", {})

        execution = RunbookExecution(
            runbook_id=runbook_id,
            runbook_version=runbook_version,
            incident_id=incident_id,
            status=ExecutionStatus.running,
            started_at=datetime.utcnow(),
            total_steps=len(steps),
            execution_context=execution_context,
        )
        await self.executions.create(execution)

        step_results: List[Dict[str, Any]] = []
        successful = failed = skipped = 0

        for index, step in enumerate(steps):
            policy = self.policy_engine.evaluate(step)
            await self.audit_logger.log(
                action="runbook_step_policy_check",
                actor="system",
                status="ok" if policy.allowed else "blocked",
                details={
                    "step_id": step.get("id"),
                    "step_type": step.get("type"),
                    "risk_level": policy.risk_level,
                    "reason": policy.reason,
                },
                runbook_execution_id=execution.id,
            )

            if not policy.allowed:
                failed += 1
                step_results.append(
                    {
                        "step_id": step.get("id"),
                        "step_name": step.get("name"),
                        "status": ExecutionStatus.failed.value,
                        "error": policy.reason,
                    }
                )
                break

            if policy.requires_approval:
                approval = await self.approval_service.request_approval(
                    runbook_execution_id=execution.id,
                    step_id=step.get("id", ""),
                    step_type=step.get("type", ""),
                    requested_by="system",
                    reason=policy.reason,
                    metadata={"step": step},
                )
                await self.audit_logger.log(
                    action="approval_requested",
                    actor="system",
                    status="pending",
                    details={
                        "approval_id": str(approval.id),
                        "step_id": step.get("id"),
                        "step_type": step.get("type"),
                    },
                    runbook_execution_id=execution.id,
                )
                execution.execution_context["pending_step_index"] = index
                execution.status = ExecutionStatus.waiting_approval
                execution.step_results = step_results
                execution.completed_at = datetime.utcnow()
                await self.session.flush()
                return execution

            executor = self.registry.get(step["type"])
            try:
                result = await executor.execute(step, execution_context)
                execution_context["step_results"][step.get("id", f"step-{index}")] = result
                step_results.append(result)
                successful += 1
            except Exception as exc:
                failed += 1
                failure_result = {
                    "step_id": step.get("id"),
                    "step_name": step.get("name"),
                    "status": ExecutionStatus.failed.value,
                    "error": str(exc),
                }
                execution_context["step_results"][step.get("id", f"step-{index}")] = failure_result
                step_results.append(
                    {
                        "step_id": step.get("id"),
                        "step_name": step.get("name"),
                        "status": ExecutionStatus.failed.value,
                        "error": str(exc),
                    }
                )
                if not step.get("continue_on_failure", False):
                    break

        execution.step_results = step_results
        execution.successful_steps = successful
        execution.failed_steps = failed
        execution.skipped_steps = skipped
        execution.completed_at = datetime.utcnow()
        execution.status = ExecutionStatus.success if failed == 0 else ExecutionStatus.failed

        try:
            duration_seconds = (execution.completed_at - execution.started_at).total_seconds()
            record_runbook_execution(
                runbook_name=runbook_id,
                status=execution.status.value,
                duration_seconds=duration_seconds,
            )
        except Exception:
            pass

        await self.session.flush()
        return execution

    async def resume_execution(self, execution_id: str) -> RunbookExecution:
        execution = await self.executions.get(execution_id)
        if not execution:
            raise ValueError("Execution not found")

        runbook_id = execution.runbook_id
        steps: List[Dict[str, Any]] = []
        if hasattr(execution, "runbook") and execution.runbook:
            steps = execution.runbook.steps
        else:
            from src.repositories import RunbookRepository

            runbook = await RunbookRepository(self.session).get(runbook_id)
            if runbook:
                steps = runbook.steps

        if not steps:
            raise ValueError("Runbook steps not found")

        if execution.execution_context is None:
            execution.execution_context = {}
        execution.execution_context.setdefault("step_results", {})
        start_index = execution.execution_context.get("pending_step_index", len(execution.step_results))
        execution.status = ExecutionStatus.running
        execution.completed_at = None

        step_results = list(execution.step_results or [])
        successful = execution.successful_steps
        failed = execution.failed_steps
        skipped = execution.skipped_steps

        for index in range(start_index, len(steps)):
            step = steps[index]
            if step.get("type") == "manual_approval":
                step_results.append(
                    {
                        "step_id": step.get("id"),
                        "step_name": step.get("name"),
                        "status": ExecutionStatus.success.value,
                        "output": {"approved": True},
                    }
                )
                successful += 1
                continue

            policy = self.policy_engine.evaluate(step)
            if not policy.allowed:
                failed += 1
                step_results.append(
                    {
                        "step_id": step.get("id"),
                        "step_name": step.get("name"),
                        "status": ExecutionStatus.failed.value,
                        "error": policy.reason,
                    }
                )
                break

            if policy.requires_approval:
                execution.execution_context["pending_step_index"] = index
                execution.status = ExecutionStatus.waiting_approval
                execution.step_results = step_results
                execution.completed_at = datetime.utcnow()
                await self.session.flush()
                return execution

            executor = self.registry.get(step["type"])
            try:
                result = await executor.execute(step, execution.execution_context)
                execution.execution_context["step_results"][step.get("id", f"step-{index}")] = result
                step_results.append(result)
                successful += 1
            except Exception as exc:
                failed += 1
                failure_result = {
                    "step_id": step.get("id"),
                    "step_name": step.get("name"),
                    "status": ExecutionStatus.failed.value,
                    "error": str(exc),
                }
                execution.execution_context["step_results"][step.get("id", f"step-{index}")] = failure_result
                step_results.append(
                    {
                        "step_id": step.get("id"),
                        "step_name": step.get("name"),
                        "status": ExecutionStatus.failed.value,
                        "error": str(exc),
                    }
                )
                if not step.get("continue_on_failure", False):
                    break

        execution.execution_context.pop("pending_step_index", None)
        execution.step_results = step_results
        execution.successful_steps = successful
        execution.failed_steps = failed
        execution.skipped_steps = skipped
        execution.completed_at = datetime.utcnow()
        execution.status = ExecutionStatus.success if failed == 0 else ExecutionStatus.failed

        try:
            duration_seconds = (execution.completed_at - execution.started_at).total_seconds()
            record_runbook_execution(
                runbook_name=execution.runbook_id,
                status=execution.status.value,
                duration_seconds=duration_seconds,
            )
        except Exception:
            pass
        await self.session.flush()
        return execution
