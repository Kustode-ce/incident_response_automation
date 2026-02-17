from dataclasses import dataclass
from typing import Any, Dict, Optional

from src.models.enums import MLTaskType


@dataclass
class MLContext:
    task: MLTaskType
    incident_id: Optional[str]
    payload: Dict[str, Any]


@dataclass
class MLPrompt:
    user_prompt: str
    system_prompt: Optional[str] = None
    context: Optional[Dict[str, Any]] = None
    temperature: float = 0.3
    max_tokens: Optional[int] = None
    
    # Aliases for backward compatibility
    @property
    def system_message(self) -> Optional[str]:
        return self.system_prompt
    
    @property
    def user_message(self) -> str:
        return self.user_prompt


@dataclass
class MLResponse:
    task: MLTaskType | None
    model_name: str
    model_version: str
    provider: str
    result: Dict[str, Any]
    confidence: Optional[float] = None
    latency_ms: Optional[float] = None
    tokens_used: Optional[int] = None
    cost_usd: Optional[float] = None
    raw_response: Optional[str] = None
    usage: Optional[Dict[str, Any]] = None
