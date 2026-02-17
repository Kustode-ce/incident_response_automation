from __future__ import annotations

from typing import Any, Dict, Optional

from src.models.enums import MLTaskType
from src.services.ml.types import MLContext


class ContextBuilder:
    async def build(self, task: MLTaskType, payload: Dict[str, Any], incident_id: Optional[str] = None) -> MLContext:
        # Placeholder: enrich with logs/metrics/k8s state.
        return MLContext(task=task, incident_id=incident_id, payload=payload)
