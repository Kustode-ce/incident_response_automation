from __future__ import annotations

import os
import time
from typing import Any, Dict

from src.models.enums import MLTaskType
from src.services.ml.codebase_analyzer import CodebaseAnalyzer
from src.services.ml.orchestrator import MLOrchestrator
from src.services.runbook.executors.base import StepExecutor
from jinja2 import Template
from src.observability.unified_observability import record_ml_inference, record_integration_request
from src.observability.metrics import record_ml_inference as record_ml_inference_metrics


_TASK_MAP = {
    "classification": MLTaskType.classification,
    "severity_prediction": MLTaskType.severity_prediction,
    "root_cause_analysis": MLTaskType.root_cause_analysis,
    "runbook_generation": MLTaskType.runbook_generation,
    "post_mortem_generation": MLTaskType.post_mortem_generation,
}


class MLAnalysisExecutor(StepExecutor):
    async def execute(self, step: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        params = step.get("params", {})

        def _render(value: Any) -> Any:
            if isinstance(value, str):
                return Template(value).render(**context)
            if isinstance(value, list):
                return [_render(item) for item in value]
            if isinstance(value, dict):
                return {key: _render(val) for key, val in value.items()}
            return value

        params = _render(params)
        task = params.get("task", "root_cause_analysis")
        incident_payload = params.get("payload") or context.get("incident", {})
        incident_id = params.get("incident_id") or context.get("incident_id")

        if task == "code_analysis":
            analyzer = CodebaseAnalyzer(
                github_token=os.getenv("GITHUB_TOKEN"),
                github_repo=os.getenv("GITHUB_REPO"),
            )
            title = params.get("title") or incident_payload.get("title", "")
            description = params.get("description") or incident_payload.get("description", "")
            service = params.get("service") or incident_payload.get("labels", {}).get("service")
            error_type = params.get("error_type")
            endpoint = params.get("endpoint")
            error_code = params.get("error_code")
            result = await analyzer.build_incident_context(
                incident_title=title,
                incident_description=description,
                service_name=service,
                error_type=error_type,
                endpoint=endpoint,
                error_code=error_code,
            )
            await analyzer.close()
        else:
            ml_task = _TASK_MAP.get(task, MLTaskType.root_cause_analysis)
            orchestrator = MLOrchestrator()
            start = time.perf_counter()
            response = await orchestrator.run(
                task=ml_task,
                payload=incident_payload,
                incident_id=incident_id,
            )
            duration = time.perf_counter() - start
            try:
                record_ml_inference(
                    provider=response.provider,
                    task=ml_task.value,
                    duration_seconds=duration,
                )
                record_ml_inference_metrics(
                    provider=response.provider,
                    task=ml_task.value,
                    duration=duration,
                    status="success",
                    input_tokens=(response.usage or {}).get("prompt_tokens", 0),
                    output_tokens=(response.usage or {}).get("completion_tokens", 0),
                )
                record_integration_request(response.provider, ml_task.value, "success")
            except Exception:
                pass
            result = response.result

        return {
            "step_id": step.get("id"),
            "step_name": step.get("name"),
            "status": "success",
            "output": {"task": task, "result": result},
        }
