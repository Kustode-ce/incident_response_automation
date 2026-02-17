from __future__ import annotations

from typing import Any, Dict, Optional

from src.models.enums import MLTaskType
from src.services.ml.context_builder import ContextBuilder
from src.services.ml.prompt_engine import PromptEngine
from src.services.ml.router import ModelRouter
from src.services.ml.types import MLResponse


class MLOrchestrator:
    def __init__(self):
        self.context_builder = ContextBuilder()
        self.prompt_engine = PromptEngine()
        self.router = ModelRouter()

    async def run(
        self,
        task: MLTaskType,
        payload: Dict[str, Any],
        incident_id: Optional[str] = None,
    ) -> MLResponse:
        context = await self.context_builder.build(task, payload, incident_id=incident_id)
        prompt = self.prompt_engine.build_prompt(context)
        provider = self.router.select(task)
        response = await provider.generate(prompt)
        response.task = task
        return response
