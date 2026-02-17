"""OpenAI provider for ML inference."""

from __future__ import annotations

import json
import logging
import os
from typing import Any, Dict, Optional

from src.services.ml.providers.base import MLProvider
from src.services.ml.types import MLPrompt, MLResponse

logger = logging.getLogger(__name__)

# Optional import - only if openai is installed
try:
    from openai import AsyncOpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    logger.warning("OpenAI SDK not installed. Install with: pip install openai")


class OpenAIProvider(MLProvider):
    """OpenAI provider for LLM inference."""

    def __init__(
        self,
        model_name: str = "gpt-4-turbo-preview",
        model_version: str = "gpt-4-0125-preview",
        api_key: Optional[str] = None,
        temperature: float = 0.3,
        max_tokens: int = 4096,
        json_mode: bool = True,
    ):
        self.model_name = model_name
        self.model_version = model_version
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.json_mode = json_mode
        self._client: Optional[Any] = None

    @property
    def client(self) -> Any:
        if not OPENAI_AVAILABLE:
            raise RuntimeError("OpenAI SDK not installed")
        if self._client is None:
            self._client = AsyncOpenAI(api_key=self.api_key)
        return self._client

    async def generate(self, prompt: MLPrompt) -> MLResponse:
        """Generate a response using OpenAI."""
        if not OPENAI_AVAILABLE or not self.api_key:
            logger.warning("OpenAI not configured, returning stub response")
            return MLResponse(
                task=None,
                model_name=self.model_name,
                model_version=self.model_version,
                provider="openai",
                result={"error": "OpenAI not configured"},
                confidence=0.0,
            )

        try:
            # Build messages
            messages = []
            
            if prompt.system_prompt:
                messages.append({"role": "system", "content": prompt.system_prompt})
            
            messages.append({"role": "user", "content": prompt.user_prompt})

            # Build request kwargs
            kwargs: Dict[str, Any] = {
                "model": self.model_version,
                "messages": messages,
                "temperature": self.temperature,
                "max_tokens": self.max_tokens,
            }

            # Enable JSON mode if requested
            if self.json_mode:
                kwargs["response_format"] = {"type": "json_object"}

            # Make the API call
            response = await self.client.chat.completions.create(**kwargs)

            # Extract content
            content = response.choices[0].message.content
            
            # Parse JSON if in JSON mode
            if self.json_mode:
                try:
                    result = json.loads(content)
                except json.JSONDecodeError:
                    result = {"raw_response": content}
            else:
                result = {"raw_response": content}

            # Calculate confidence based on response
            confidence = self._calculate_confidence(result, response)

            # Track usage
            usage = {
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
                "total_tokens": response.usage.total_tokens,
            }

            logger.info(
                f"OpenAI response: model={self.model_version}, "
                f"tokens={usage['total_tokens']}"
            )

            return MLResponse(
                task=None,  # Filled by orchestrator
                model_name=self.model_name,
                model_version=self.model_version,
                provider="openai",
                result=result,
                confidence=confidence,
                usage=usage,
            )

        except Exception as e:
            logger.error(f"OpenAI API error: {e}")
            return MLResponse(
                task=None,
                model_name=self.model_name,
                model_version=self.model_version,
                provider="openai",
                result={"error": str(e)},
                confidence=0.0,
            )

    def _calculate_confidence(self, result: Dict[str, Any], response: Any) -> float:
        """Calculate confidence score from response."""
        # If result contains a confidence field, use it
        if "confidence" in result:
            try:
                return float(result["confidence"])
            except (ValueError, TypeError):
                pass

        # Default confidence based on finish reason
        finish_reason = response.choices[0].finish_reason
        if finish_reason == "stop":
            return 0.85
        elif finish_reason == "length":
            return 0.6  # Response was truncated
        else:
            return 0.5

    async def classify_incident(
        self, incident_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Classify an incident using the model."""
        system_prompt = """You are an incident classification expert. 
Analyze the incident and provide:
1. category: infrastructure, application, database, network, security, or other
2. severity: critical, high, medium, low, or info
3. affected_components: list of affected system components
4. confidence: your confidence level (0.0-1.0)
5. reasoning: brief explanation

Respond in JSON format."""

        user_prompt = f"""Classify this incident:

Title: {incident_data.get('title', 'Unknown')}
Description: {incident_data.get('description', 'No description')}
Labels: {json.dumps(incident_data.get('labels', {}))}
Alert Source: {incident_data.get('source', 'unknown')}
"""

        prompt = MLPrompt(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            context=incident_data,
        )

        response = await self.generate(prompt)
        return response.result

    async def analyze_root_cause(
        self,
        incident_data: Dict[str, Any],
        logs: Optional[str] = None,
        metrics: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Analyze root cause of an incident."""
        system_prompt = """You are an SRE expert performing root cause analysis.
Analyze the incident data, logs, and metrics to determine:
1. root_cause: the most likely root cause
2. contributing_factors: list of contributing factors
3. affected_services: services impacted
4. timeline: sequence of events leading to the incident
5. confidence: your confidence in this analysis (0.0-1.0)
6. recommendations: immediate actions to take

Respond in JSON format."""

        user_prompt = f"""Analyze this incident:

Title: {incident_data.get('title', 'Unknown')}
Description: {incident_data.get('description', 'No description')}
Severity: {incident_data.get('severity', 'unknown')}
Category: {incident_data.get('category', 'unknown')}

"""
        if logs:
            user_prompt += f"Recent Logs:\n```\n{logs[:5000]}\n```\n\n"
        
        if metrics:
            user_prompt += f"Metrics:\n{json.dumps(metrics, indent=2)}\n"

        prompt = MLPrompt(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            context=incident_data,
        )

        response = await self.generate(prompt)
        return response.result

    async def generate_runbook(
        self,
        incident_data: Dict[str, Any],
        available_actions: Optional[list] = None,
    ) -> Dict[str, Any]:
        """Generate a runbook for incident response."""
        system_prompt = """You are an SRE automation expert.
Generate a runbook to remediate this incident. The runbook should include:
1. name: descriptive name for the runbook
2. description: what this runbook does
3. steps: list of steps, each with:
   - id: unique step identifier
   - type: notification, kubernetes, http_request, wait, conditional, or manual_approval
   - description: what this step does
   - config: configuration for the step
4. estimated_duration: estimated time to complete
5. risk_level: low, medium, or high
6. requires_approval: whether manual approval is needed

Respond in JSON format."""

        user_prompt = f"""Generate a runbook for this incident:

Title: {incident_data.get('title', 'Unknown')}
Description: {incident_data.get('description', 'No description')}
Severity: {incident_data.get('severity', 'unknown')}
Category: {incident_data.get('category', 'unknown')}
Labels: {json.dumps(incident_data.get('labels', {}))}
"""

        if available_actions:
            user_prompt += f"\nAvailable action types: {', '.join(available_actions)}"

        prompt = MLPrompt(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            context=incident_data,
        )

        response = await self.generate(prompt)
        return response.result
