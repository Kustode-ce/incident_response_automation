from __future__ import annotations

from typing import Dict

from src.models.enums import MLTaskType
from src.services.ml.providers.anthropic_provider import AnthropicProvider
from src.services.ml.providers.openai_provider import OpenAIProvider
from src.services.ml.providers.base import MLProvider


class ModelRouter:
    def __init__(self):
        self._routes: Dict[MLTaskType, MLProvider] = {
            MLTaskType.classification: OpenAIProvider("gpt-4-turbo", "gpt-4"),
            MLTaskType.severity_prediction: OpenAIProvider("gpt-3.5-turbo", "gpt-3.5"),
            MLTaskType.root_cause_analysis: OpenAIProvider(
                "gpt-4-turbo",
                "gpt-4",
                json_mode=False,
            ),
            MLTaskType.runbook_generation: OpenAIProvider("gpt-4-turbo", "gpt-4"),
            MLTaskType.post_mortem_generation: AnthropicProvider("claude-3-opus", "claude-3-opus"),
        }

    def select(self, task: MLTaskType) -> MLProvider:
        return self._routes[task]
