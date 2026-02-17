from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict


class StepExecutor(ABC):
    @abstractmethod
    async def execute(self, step: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        raise NotImplementedError
