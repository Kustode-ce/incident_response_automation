from __future__ import annotations

from typing import Any, Dict, List, Optional

from jinja2 import Template

from src.config.integrations_config import load_integrations_config
from src.services.integrations import GitHubIntegration, JiraIntegration, SlackIntegration
from src.observability.unified_observability import record_integration_request

from src.services.runbook.executors.base import StepExecutor


class NotificationExecutor(StepExecutor):
    async def execute(self, step: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        params = step.get("params", {})
        integration = params.get("integration", "slack")
        config = load_integrations_config()
        def _normalize(value: Optional[str]) -> Optional[str]:
            if not isinstance(value, str):
                return value
            if (value.startswith('"') and value.endswith('"')) or (value.startswith("'") and value.endswith("'")):
                return value[1:-1]
            return value

        output: Dict[str, Any] = {}

        def _render(value: Any) -> Any:
            if isinstance(value, str):
                return Template(value).render(**context)
            if isinstance(value, list):
                return [_render(item) for item in value]
            if isinstance(value, dict):
                return {key: _render(val) for key, val in value.items()}
            return value

        action = params.get("action", "create")

        if integration == "slack":
            slack_cfg = config.get("communication", {}).get("slack", {})
            if not slack_cfg.get("enabled", False):
                raise ValueError("Slack integration is disabled.")
            slack = SlackIntegration(
                {
                    "bot_token": slack_cfg.get("bot_token"),
                    "webhook_url": slack_cfg.get("webhook_url"),
                    "default_channel": slack_cfg.get("channels", {}).get("incidents"),
                }
            )
            message = _render(params.get("message", ""))
            channel = _render(params.get("channel"))
            blocks = _render(params.get("blocks"))
            try:
                output = await slack.send_notification(
                    message=message,
                    channel=channel,
                    blocks=blocks,
                )
                record_integration_request("slack", action, "success")
            except Exception:
                record_integration_request("slack", action, "error")
                raise

        elif integration == "jira":
            jira_cfg = config.get("incident_management", {}).get("jira", {})
            if not jira_cfg.get("enabled", False):
                raise ValueError("Jira integration is disabled.")
            jira = JiraIntegration(
                url=_normalize(jira_cfg.get("url", "")) or "",
                username=_normalize(jira_cfg.get("username", "")) or "",
                api_token=_normalize(jira_cfg.get("api_token", "")) or "",
                project_key=_normalize(jira_cfg.get("project_key", "INC")) or "INC",
                issue_type=_normalize(params.get("issue_type"))
                or _normalize(jira_cfg.get("issue_type", "Bug"))
                or "Bug",
            )
            try:
                if action == "comment":
                    ticket_key = _render(params.get("ticket_key"))
                    comment = _render(params.get("comment") or params.get("message", ""))
                    if not ticket_key:
                        raise ValueError("Jira comment requires params.ticket_key")
                    output = await jira.add_comment(ticket_key=str(ticket_key), comment=str(comment))
                else:
                    summary = _render(params.get("summary") or "Incident response ticket")
                    description = _render(params.get("description") or params.get("message", ""))
                    priority = _render(params.get("priority", "Medium"))
                    labels: Optional[List[str]] = _render(params.get("labels"))
                    components: Optional[List[str]] = _render(params.get("components"))
                    incident_id = _render(params.get("incident_id") or context.get("incident_id"))
                    output = await jira.create_ticket(
                        summary=summary,
                        description=description,
                        priority=priority,
                        labels=labels,
                        components=components,
                        incident_id=incident_id,
                    )
                record_integration_request("jira", action, "success")
            except Exception:
                record_integration_request("jira", action, "error")
                raise
            await jira.close()

        elif integration == "github":
            github_cfg = config.get("version_control", {}).get("github", {})
            if not github_cfg.get("enabled", False):
                raise ValueError("GitHub integration is disabled.")
            github = GitHubIntegration(
                token=github_cfg.get("token", ""),
                repository=github_cfg.get("repository", ""),
                api_url=github_cfg.get("api_url", "https://api.github.com"),
            )
            try:
                if action == "comment":
                    issue_number = _render(params.get("issue_number"))
                    body = _render(params.get("body") or params.get("message", ""))
                    if not issue_number:
                        raise ValueError("GitHub comment requires params.issue_number")
                    output = await github.add_comment(issue_number=int(issue_number), body=str(body))
                else:
                    title = _render(params.get("title") or "Incident response issue")
                    body = _render(params.get("body") or params.get("message", ""))
                    labels: Optional[List[str]] = _render(params.get("labels"))
                    output = await github.create_issue(
                        title=title,
                        body=body,
                        labels=labels,
                        incident_id=_render(params.get("incident_id") or context.get("incident_id")),
                    )
                record_integration_request("github", action, "success")
            except Exception:
                record_integration_request("github", action, "error")
                raise
            await github.close()

        else:
            raise ValueError(f"Unsupported integration for notification: {integration}")

        return {
            "step_id": step.get("id"),
            "step_name": step.get("name"),
            "status": "success",
            "output": output,
        }
