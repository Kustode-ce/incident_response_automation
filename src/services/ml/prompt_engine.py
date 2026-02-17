from __future__ import annotations

from src.services.ml.types import MLContext, MLPrompt


class PromptEngine:
    def build_prompt(self, context: MLContext) -> MLPrompt:
        system_message = "You are an incident response assistant."
        user_message = f"Task: {context.task.value}. Payload: {context.payload}"
        return MLPrompt(system_prompt=system_message, user_prompt=user_message)
