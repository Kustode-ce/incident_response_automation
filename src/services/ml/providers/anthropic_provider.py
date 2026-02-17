"""Anthropic Claude provider for ML inference."""

from __future__ import annotations

import json
import logging
import os
from typing import Any, Dict, Optional

from src.services.ml.providers.base import MLProvider
from src.services.ml.types import MLPrompt, MLResponse

logger = logging.getLogger(__name__)

# Optional import - only if anthropic is installed
try:
    from anthropic import AsyncAnthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False
    logger.warning("Anthropic SDK not installed. Install with: pip install anthropic")


class AnthropicProvider(MLProvider):
    """Anthropic Claude provider for LLM inference."""

    def __init__(
        self,
        model_name: str = "claude-3-opus-20240229",
        model_version: str = "claude-3-opus-20240229",
        api_key: Optional[str] = None,
        temperature: float = 0.5,
        max_tokens: int = 4096,
    ):
        self.model_name = model_name
        self.model_version = model_version
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        self.temperature = temperature
        self.max_tokens = max_tokens
        self._client: Optional[Any] = None

    @property
    def client(self) -> Any:
        if not ANTHROPIC_AVAILABLE:
            raise RuntimeError("Anthropic SDK not installed")
        if self._client is None:
            self._client = AsyncAnthropic(api_key=self.api_key)
        return self._client

    async def generate(self, prompt: MLPrompt) -> MLResponse:
        """Generate a response using Anthropic Claude."""
        if not ANTHROPIC_AVAILABLE or not self.api_key:
            logger.warning("Anthropic not configured, returning stub response")
            return MLResponse(
                task=None,
                model_name=self.model_name,
                model_version=self.model_version,
                provider="anthropic",
                result={"error": "Anthropic not configured"},
                confidence=0.0,
            )

        try:
            # Build the request
            kwargs: Dict[str, Any] = {
                "model": self.model_version,
                "max_tokens": self.max_tokens,
                "temperature": self.temperature,
                "messages": [{"role": "user", "content": prompt.user_prompt}],
            }

            # Add system prompt if provided
            if prompt.system_prompt:
                kwargs["system"] = prompt.system_prompt

            # Make the API call
            response = await self.client.messages.create(**kwargs)

            # Extract content
            content = response.content[0].text

            # Try to parse as JSON
            try:
                # Look for JSON in the response
                if "```json" in content:
                    json_start = content.find("```json") + 7
                    json_end = content.find("```", json_start)
                    json_str = content[json_start:json_end].strip()
                    result = json.loads(json_str)
                elif content.strip().startswith("{"):
                    result = json.loads(content)
                else:
                    result = {"raw_response": content}
            except json.JSONDecodeError:
                result = {"raw_response": content}

            # Calculate confidence
            confidence = self._calculate_confidence(result, response)

            # Track usage
            usage = {
                "input_tokens": response.usage.input_tokens,
                "output_tokens": response.usage.output_tokens,
                "total_tokens": response.usage.input_tokens + response.usage.output_tokens,
            }

            logger.info(
                f"Anthropic response: model={self.model_version}, "
                f"tokens={usage['total_tokens']}"
            )

            return MLResponse(
                task=None,  # Filled by orchestrator
                model_name=self.model_name,
                model_version=self.model_version,
                provider="anthropic",
                result=result,
                confidence=confidence,
                usage=usage,
            )

        except Exception as e:
            logger.error(f"Anthropic API error: {e}")
            return MLResponse(
                task=None,
                model_name=self.model_name,
                model_version=self.model_version,
                provider="anthropic",
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

        # Default confidence based on stop reason
        stop_reason = response.stop_reason
        if stop_reason == "end_turn":
            return 0.85
        elif stop_reason == "max_tokens":
            return 0.6  # Response was truncated
        else:
            return 0.5

    async def analyze_root_cause(
        self,
        incident_data: Dict[str, Any],
        logs: Optional[str] = None,
        metrics: Optional[Dict[str, Any]] = None,
        kubernetes_state: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Analyze root cause of an incident.
        
        Claude excels at reasoning and analysis, making it ideal for RCA.
        """
        system_prompt = """You are a world-class Site Reliability Engineer performing root cause analysis.

Your task is to analyze incident data, logs, metrics, and system state to determine the root cause.

Be thorough, methodical, and evidence-based in your analysis. Consider:
1. Timeline of events
2. Correlation between metrics and symptoms
3. System dependencies and cascading failures
4. Common failure patterns

Provide your analysis in JSON format with these fields:
{
  "root_cause": "Primary root cause description",
  "root_cause_category": "One of: configuration, code_bug, infrastructure, dependency, capacity, security, unknown",
  "confidence": 0.0-1.0,
  "evidence": ["List of evidence supporting this conclusion"],
  "contributing_factors": ["Additional factors that contributed"],
  "timeline": [
    {"time": "timestamp or relative time", "event": "what happened"}
  ],
  "affected_services": ["list of impacted services"],
  "blast_radius": "low/medium/high",
  "recommendations": {
    "immediate": ["Actions to take now"],
    "short_term": ["Actions for next 24-48 hours"],
    "long_term": ["Preventive measures"]
  }
}"""

        user_prompt = f"""Analyze this incident and determine the root cause:

## Incident Details
- **Title:** {incident_data.get('title', 'Unknown')}
- **Description:** {incident_data.get('description', 'No description')}
- **Severity:** {incident_data.get('severity', 'unknown')}
- **Category:** {incident_data.get('category', 'unknown')}
- **Labels:** {json.dumps(incident_data.get('labels', {}), indent=2)}

"""
        if logs:
            user_prompt += f"""## Recent Logs
```
{logs[:8000]}
```

"""

        if metrics:
            user_prompt += f"""## Metrics Data
```json
{json.dumps(metrics, indent=2)[:3000]}
```

"""

        if kubernetes_state:
            user_prompt += f"""## Kubernetes State
```json
{json.dumps(kubernetes_state, indent=2)[:3000]}
```

"""

        user_prompt += """
Please analyze all available data and provide your root cause analysis in JSON format."""

        prompt = MLPrompt(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            context=incident_data,
        )

        response = await self.generate(prompt)
        return response.result

    async def generate_postmortem(
        self,
        incident_data: Dict[str, Any],
        root_cause_analysis: Optional[Dict[str, Any]] = None,
        resolution_steps: Optional[list] = None,
    ) -> Dict[str, Any]:
        """
        Generate a post-mortem report for an incident.
        
        Claude's writing ability makes it excellent for comprehensive post-mortems.
        """
        system_prompt = """You are an expert technical writer creating blameless post-mortem reports.

Create a comprehensive post-mortem that is:
- Blameless and focused on systems, not individuals
- Clear and accessible to both technical and non-technical readers
- Actionable with specific follow-up items
- Educational to prevent similar incidents

Provide the post-mortem in JSON format with these fields:
{
  "title": "Post-mortem title",
  "summary": "Executive summary (2-3 sentences)",
  "impact": {
    "duration_minutes": estimated duration,
    "affected_users": "description of user impact",
    "affected_services": ["list of services"],
    "severity": "P1/P2/P3/P4"
  },
  "timeline": [
    {"time": "timestamp", "event": "what happened", "actor": "person or system"}
  ],
  "root_cause": "Detailed root cause explanation",
  "contributing_factors": ["List of contributing factors"],
  "detection": {
    "how_detected": "How was this discovered",
    "time_to_detect": "How long until detection",
    "detection_gaps": "What could have detected it sooner"
  },
  "resolution": {
    "steps_taken": ["List of resolution steps"],
    "time_to_resolve": "Resolution time",
    "what_worked": "What helped",
    "what_didnt_work": "What didn't help"
  },
  "lessons_learned": ["Key takeaways"],
  "action_items": [
    {
      "action": "What needs to be done",
      "owner": "Team or role responsible",
      "priority": "P1/P2/P3",
      "due_date": "Suggested timeline"
    }
  ],
  "appendix": {
    "related_incidents": ["Links to similar past incidents"],
    "references": ["Relevant documentation links"]
  }
}"""

        user_prompt = f"""Create a post-mortem for this incident:

## Incident Details
- **Title:** {incident_data.get('title', 'Unknown')}
- **Description:** {incident_data.get('description', 'No description')}
- **Severity:** {incident_data.get('severity', 'unknown')}
- **Category:** {incident_data.get('category', 'unknown')}
- **Created:** {incident_data.get('created_at', 'unknown')}
- **Resolved:** {incident_data.get('resolved_at', 'unknown')}

"""

        if root_cause_analysis:
            user_prompt += f"""## Root Cause Analysis
```json
{json.dumps(root_cause_analysis, indent=2)}
```

"""

        if resolution_steps:
            user_prompt += f"""## Resolution Steps Taken
{json.dumps(resolution_steps, indent=2)}

"""

        user_prompt += """
Generate a comprehensive, blameless post-mortem in JSON format."""

        prompt = MLPrompt(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            context=incident_data,
        )

        response = await self.generate(prompt)
        return response.result

    async def suggest_remediation(
        self,
        incident_data: Dict[str, Any],
        available_actions: list,
    ) -> Dict[str, Any]:
        """Suggest remediation actions for an incident."""
        system_prompt = f"""You are an SRE automation expert suggesting remediation actions.

Available automated actions:
{json.dumps(available_actions, indent=2)}

Analyze the incident and suggest appropriate remediation actions.

Respond in JSON format:
{{
  "recommended_actions": [
    {{
      "action_type": "type from available_actions",
      "description": "why this action",
      "config": {{}},  // action-specific configuration
      "risk_level": "low/medium/high",
      "requires_approval": true/false
    }}
  ],
  "manual_steps": ["Steps that require human intervention"],
  "confidence": 0.0-1.0,
  "warnings": ["Any risks or caveats"]
}}"""

        user_prompt = f"""Suggest remediation for this incident:

Title: {incident_data.get('title', 'Unknown')}
Description: {incident_data.get('description', 'No description')}
Severity: {incident_data.get('severity', 'unknown')}
Category: {incident_data.get('category', 'unknown')}
Labels: {json.dumps(incident_data.get('labels', {}))}
"""

        prompt = MLPrompt(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            context=incident_data,
        )

        response = await self.generate(prompt)
        return response.result
