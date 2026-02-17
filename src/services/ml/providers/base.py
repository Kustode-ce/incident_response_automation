from __future__ import annotations

from abc import ABC, abstractmethod

from src.services.ml.types import MLPrompt, MLResponse


class MLProvider(ABC):
    @abstractmethod
    async def generate(self, prompt: MLPrompt) -> MLResponse:
        raise NotImplementedError
