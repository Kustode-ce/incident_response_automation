import json
import os
import time
from datetime import datetime, timezone
from uuid import uuid4

import httpx


def _env(name: str, default: str) -> str:
    value = os.getenv(name, default)
    if value is None:
        return default
    if isinstance(value, str) and len(value) >= 2:
        if (value.startswith('"') and value.endswith('"')) or (value.startswith("'") and value.endswith("'")):
            return value[1:-1]
    return value


API_BASE = _env("API_BASE_URL", "http://localhost:8000")
LOKI_URL = _env("LOKI_URL", "http://localhost:3100")
PROM_URL = _env("PROMETHEUS_URL", "http://localhost:9090")
SLACK_CHANNEL = _env("SLACK_INCIDENTS_CHANNEL", "#incidents")
JIRA_ISSUE_TYPE = _env("JIRA_ISSUE_TYPE", "Submit a request or incident")


def post_json(client: httpx.Client, url: str, payload: dict) -> httpx.Response:
    resp = client.post(url, json=payload, timeout=30)
    resp.raise_for_status()
    return resp


def push_loki_logs(client: httpx.Client) -> None:
    now = datetime.now(timezone.utc)
    ts_ns = int(now.timestamp() * 1_000_000_000)
    payload = {
        "streams": [
            {
                "stream": {
                    "service": "incident-api",
                    "environment": "demo",
                    "severity": "error",
                },
                "values": [
                    [str(ts_ns), "ERROR Database connection pool exhausted (demo)"],
                    [str(ts_ns + 1_000_000), "ERROR Upstream latency spike detected (demo)"],
                ],
            }
        ]
    }
    post_json(client, f"{LOKI_URL}/loki/api/v1/push", payload)


def send_alertmanager_webhook(client: httpx.Client, incident_id: str) -> None:
    payload = {
        "status": "firing",
        "alerts": [
            {
                "status": "firing",
                "labels": {
                    "alertname": "HighCPUUsage",
                    "severity": "critical",
                    "service": "incident-api",
                    "namespace": "demo",
                    "incident_id": incident_id,
                },
                "annotations": {
                    "summary": "High CPU on incident-api",
                    "description": "CPU > 90% for 5m",
                },
                "startsAt": datetime.now(timezone.utc).isoformat(),
            }
        ],
    }
    post_json(client, f"{API_BASE}/webhooks/alertmanager", payload)


def create_incident_and_alert(client: httpx.Client) -> tuple[str, str, dict]:
    incident_payload = {
        "fingerprint": f"demo-{uuid4().hex[:12]}",
        "title": "Demo: Payment Gateway Latency Spike",
        "description": "Simulated latency regression in incident-api (production demo)",
        "category": "application",
        "severity": "high",
        "status": "new",
        "labels": {
            "service": "incident-api",
            "pod": "incident-api-1",
            "namespace": "demo",
        },
        "metadata": {"source": "demo-script"},
        "created_by": "demo",
    }
    incident = post_json(client, f"{API_BASE}/incidents/", incident_payload).json()
    alert_payload = {
        "source": "alertmanager",
        "status": "firing",
        "severity": "high",
        "message": "High CPU usage detected",
        "fingerprint": f"alert-{uuid4().hex[:12]}",
        "labels": incident_payload["labels"],
        "annotations": {"runbook": "demo-production-flow"},
        "incident_id": incident["id"],
    }
    alert = post_json(client, f"{API_BASE}/alerts/", alert_payload).json()
    return incident["id"], alert["id"], incident_payload


def _slack_blocks_for_incident(incident_id: str) -> list[dict]:
    jira_url = "{{ step_results['jira-ticket'].output.url }}"
    github_url = "{{ step_results['github-issue'].output.url }}"
    rc_summary = "{{ step_results['ml-root-cause'].output.result.raw_response | default(step_results['ml-root-cause'].output.result.root_cause) | default('Pending analysis') }}"
    timeline = "{{ timeline | join('\\n') }}"
    runbook_steps = "{{ runbook_steps | join('\\n') }}"
    log_excerpts = "{{ log_excerpts | join('\\n') }}"
    metrics_status = "{{ step_results['query-metrics'].output.value.data.result[0].value[1] | default('n/a') }}"
    metrics_instance = "{{ step_results['query-metrics'].output.value.data.result[0].metric.instance | default('n/a') }}"
    return [
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*AI Root Cause Analysis*\n{rc_summary}",
            },
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "*Contributing Factors*\n• High memory utilization (>90%)\n• Database connection pool exhausted\n• Upstream service latency spike",
            },
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "*Recommended Actions*\n1. Scale up affected service replicas\n2. Clear database connection pool\n3. Enable circuit breaker for upstream calls\n4. Review recent deployments",
            },
        },
        {
            "type": "section",
            "fields": [
                {"type": "mrkdwn", "text": "*Affected Users:*\n~2,500"},
                {"type": "mrkdwn", "text": "*SLA Risk:*\nHigh"},
            ],
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*Metrics Snapshot*\n• incident-api up: `{metrics_status}`\n• instance: `{metrics_instance}`",
            },
        },
        {
            "type": "section",
            "text": {"type": "mrkdwn", "text": f"*Timeline*\n{timeline}"},
        },
        {
            "type": "section",
            "text": {"type": "mrkdwn", "text": f"*Runbook Steps*\n{runbook_steps}"},
        },
        {
            "type": "section",
            "text": {"type": "mrkdwn", "text": f"*Log Excerpts*\n{log_excerpts}"},
        },
        {
            "type": "context",
            "elements": [
                {"type": "mrkdwn", "text": f"*Jira:* <{jira_url}|View ticket>"},
                {"type": "mrkdwn", "text": f"*GitHub:* <{github_url}|View issue>"},
            ],
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": (
                    "*Incident*\n*Payment Gateway Latency Spike*\n"
                    "Severity: *HIGH*\nCategory: application\nStatus: new\n"
                    f"Incident ID: `{incident_id[:8]}`"
                ),
            },
        },
    ]


def create_and_execute_runbook(client: httpx.Client, incident_id: str, incident_payload: dict) -> dict:
    runbook_payload = {
        "name": "Demo: Production Alert Flow",
        "description": "Simulates end-to-end alert ingestion, analysis, and notifications",
        "version": "1.0.0",
        "enabled": True,
        "trigger_conditions": None,
        "steps": [
            {
                "id": "query-metrics",
                "name": "Query Prometheus",
                "type": "query_metrics",
                "params": {"query": 'up{job="incident-api"}'},
            },
            {
                "id": "query-logs",
                "name": "Query Loki",
                "type": "query_logs",
                "params": {"query": '{service="incident-api"} |= "ERROR"', "limit": 50},
            },
            {
                "id": "jira-ticket",
                "name": "Create Jira ticket",
                "type": "notification",
                "params": {
                    "integration": "jira",
                    "summary": "{{ incident_title }}",
                    "description": (
                        "Automated Jira ticket from demo production flow\n\n"
                        "Incident ID: {{ incident_id }}\n"
                        "Title: {{ incident_title }}\n"
                        "Description: {{ incident_description }}\n"
                        "Service: {{ incident.labels.service }}\n"
                        "Severity: {{ incident.severity }}\n"
                        "Category: {{ incident.category }}\n"
                        "\n"
                        "Timeline:\n"
                        "{{ timeline | join('\\n') }}\n"
                        "\n"
                        "Runbook Steps:\n"
                        "{{ runbook_steps | join('\\n') }}\n"
                        "\n"
                        "Log Excerpts:\n"
                        "{{ log_excerpts | join('\\n') }}\n"
                    ),
                    "priority": "High",
                    "issue_type": JIRA_ISSUE_TYPE,
                    "labels": ["incident", "demo"],
                    "incident_id": "{{ incident_id }}",
                },
            },
            {
                "id": "github-issue",
                "name": "Create GitHub issue",
                "type": "notification",
                "params": {
                    "integration": "github",
                    "title": "{{ incident_title }}",
                    "body": (
                        "## Incident Details\n"
                        "| Field | Value |\n"
                        "|------|-------|\n"
                        "| Incident ID | `{{ incident_id }}` |\n"
                        "| Title | {{ incident_title }} |\n"
                        "| Severity | {{ incident.severity }} |\n"
                        "| Category | {{ incident.category }} |\n"
                        "| Service | {{ incident.labels.service }} |\n"
                        "\n"
                        "## Description\n"
                        "{{ incident_description }}\n"
                        "\n"
                        "## Timeline\n"
                        "{{ timeline | join('\\n') }}\n"
                        "\n"
                        "## Runbook Steps\n"
                        "{{ runbook_steps | join('\\n') }}\n"
                        "\n"
                        "## Log Excerpts\n"
                        "{{ log_excerpts | join('\\n') }}\n"
                    ),
                    "labels": ["incident", "demo"],
                    "incident_id": "{{ incident_id }}",
                },
            },
            {
                "id": "ml-root-cause",
                "name": "Root cause analysis",
                "type": "ml_analysis",
                "params": {
                    "task": "root_cause_analysis",
                    "payload": {
                        "title": "{{ incident_title }}",
                        "description": "{{ incident_description }}",
                        "severity": "{{ incident.severity }}",
                        "category": "{{ incident.category }}",
                        "labels": "{{ incident.labels }}",
                        "metrics": "{{ step_results['query-metrics'].output.value }}",
                        "logs": "{{ step_results['query-logs'].output.logs }}",
                    },
                },
            },
            {
                "id": "notify-slack",
                "name": "Slack incident notification",
                "type": "notification",
                "params": {
                    "integration": "slack",
                    "channel": SLACK_CHANNEL,
                    "message": "AI Root Cause Analysis — Payment Gateway Latency Spike",
                    "blocks": _slack_blocks_for_incident(incident_id),
                },
            },
            {
                "id": "jira-comment",
                "name": "Update Jira with analysis",
                "type": "notification",
                "params": {
                    "integration": "jira",
                    "action": "comment",
                    "ticket_key": "{{ step_results['jira-ticket'].output.key }}",
                    "comment": (
                        "AI Root Cause Analysis:\n"
                        "{{ step_results['ml-root-cause'].output.result.raw_response | default(step_results['ml-root-cause'].output.result.root_cause) | default('Pending analysis') }}\n\n"
                        "Recommendations:\n"
                        "{{ step_results['ml-root-cause'].output.result.recommendations | default([]) }}\n"
                    ),
                },
            },
            {
                "id": "github-comment",
                "name": "Update GitHub with analysis",
                "type": "notification",
                "params": {
                    "integration": "github",
                    "action": "comment",
                    "issue_number": "{{ step_results['github-issue'].output.number }}",
                    "body": (
                        "## AI Root Cause Analysis\n"
                        "{{ step_results['ml-root-cause'].output.result.raw_response | default(step_results['ml-root-cause'].output.result.root_cause) | default('Pending analysis') }}\n\n"
                        "## Recommendations\n"
                        "{{ step_results['ml-root-cause'].output.result.recommendations | default([]) }}\n"
                    ),
                },
            },
            {
                "id": "code-analysis",
                "name": "Code analysis",
                "type": "ml_analysis",
                "params": {
                    "task": "code_analysis",
                    "title": "Payment Gateway Latency Spike",
                    "description": "Simulated latency regression in incident-api",
                },
            },
        ],
        "rollback_steps": None,
        "created_by": "demo",
        "tags": ["demo", "production"],
        "auto_execute": False,
        "max_concurrent_executions": 1,
    }
    runbook = post_json(client, f"{API_BASE}/runbooks/", runbook_payload).json()
    now = datetime.now(timezone.utc)
    timeline = [
        f"{now.isoformat()} - Alert received",
        f"{now.isoformat()} - Incident created",
        f"{now.isoformat()} - Runbook started",
    ]
    runbook_steps = [
        "query-metrics: Query Prometheus",
        "query-logs: Query Loki",
        "jira-ticket: Create Jira ticket",
        "github-issue: Create GitHub issue",
        "ml-root-cause: Root cause analysis",
        "notify-slack: Slack incident notification",
        "jira-comment: Update Jira with analysis",
        "github-comment: Update GitHub with analysis",
        "code-analysis: Code analysis",
    ]
    log_excerpts = [
        f"{now.isoformat()} - ERROR Database connection pool exhausted (demo)",
        f"{now.isoformat()} - ERROR Upstream latency spike detected (demo)",
    ]
    execution_context = {
        "incident_id": incident_id,
        "incident_title": incident_payload.get("title"),
        "incident_description": incident_payload.get("description"),
        "incident": incident_payload,
        "timeline": timeline,
        "runbook_steps": runbook_steps,
        "log_excerpts": log_excerpts,
    }
    execution = post_json(
        client,
        f"{API_BASE}/runbooks/{runbook['id']}/execute",
        {"incident_id": incident_id, "execution_context": execution_context},
    ).json()
    return {"runbook_id": runbook["id"], "execution": execution}


def main() -> None:
    print("== Demo production flow ==")
    print(f"API_BASE: {API_BASE}")
    print(f"LOKI_URL: {LOKI_URL}")
    print(f"PROMETHEUS_URL: {PROM_URL}")

    with httpx.Client() as client:
        incident_id, alert_id, incident_payload = create_incident_and_alert(client)
        print(f"Incident: {incident_id}")
        print(f"Alert: {alert_id}")

        send_alertmanager_webhook(client, incident_id)
        print("Alertmanager webhook: sent")

        push_loki_logs(client)
        print("Loki logs: pushed")

        # Small delay to ensure logs are queryable
        time.sleep(1.0)

        result = create_and_execute_runbook(client, incident_id, incident_payload)
        print(f"Runbook: {result['runbook_id']}")
        print(f"Execution status: {result['execution'].get('status')}")
        print(json.dumps(result["execution"].get("step_results", []), indent=2))


if __name__ == "__main__":
    main()
