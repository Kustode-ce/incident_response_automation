from __future__ import annotations

from typing import Any, Callable, Dict


class IntegrationError(Exception):
    pass


class BaseIntegration:
    def __init__(self, config: Dict[str, Any]):
        self.config = config

    async def test_connection(self) -> bool:
        return True

    async def execute_with_circuit_breaker(self, func: Callable, *args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except Exception as exc:
            raise IntegrationError(str(exc)) from exc
