from __future__ import annotations

import json
import logging
import os
import re
from datetime import datetime, timezone
from typing import Any, Dict, Optional
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from src.config.integrations_config import load_integrations_config
from src.models.schemas.base import APIModel
from src.observability.metrics import record_copilot_message, record_copilot_ticket_update
from src.models import Alert, Incident
from src.repositories import AlertRepository, CopilotConversationRepository, IncidentRepository
from src.models.enums import MLTaskType
from src.services.integrations.github import GitHubIntegration
from src.services.integrations.grafana import GrafanaIntegration
from src.services.integrations.jira import JiraIntegration
from src.services.integrations.loki import LokiIntegration
from src.services.integrations.prometheus import PrometheusIntegration
from src.services.ml.router import ModelRouter
from src.services.ml.types import MLPrompt
from src.utils.database import get_db_session, get_db_session_context

router = APIRouter(prefix="/copilot", tags=["Copilot"])
logger = logging.getLogger(__name__)

MAX_HISTORY_MESSAGES = 12
TICKET_UPDATE_EVERY = 2
MAX_QUERY_LENGTH = 300
MAX_LOG_LINES = 10
MAX_PROM_SERIES = 3
MAX_CONTEXT_INCIDENTS = 5
MAX_CONTEXT_ALERTS = 5
MAX_CODE_RESULTS = 3
CODE_ROOT = "/app/src"
DEFAULT_STAGE = "triage"


class CopilotChatRequest(APIModel):
    prompt: str
    incident_id: Optional[UUID] = None
    user_id: Optional[str] = None
    channel_id: Optional[str] = None
    source: Optional[str] = "api"


class CopilotChatResponse(APIModel):
    status: str
    response: Dict[str, Any]


async def _incident_context(
    session: AsyncSession,
    incident_id: Optional[UUID],
) -> Dict[str, Any]:
    if not incident_id:
        return {}
    repo = IncidentRepository(session)
    incident = await repo.get(incident_id)
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")
    return {
        "id": str(incident.id),
        "title": incident.title,
        "description": incident.description,
        "severity": incident.severity,
        "category": incident.category,
        "status": incident.status,
        "labels": incident.labels,
        "metadata": incident.extra_data,
    }


def _format_history(messages: list) -> str:
    if not messages:
        return "No prior conversation."
    lines = []
    for message in messages:
        content = (message.content or "").strip()
        if content:
            lines.append(f"{message.role}: {content}")
    return "\n".join(lines) if lines else "No prior conversation."


def _build_copilot_prompt(
    question: str,
    context: Dict[str, Any],
    summary: Optional[str],
    history_text: str,
    observability: Optional[Dict[str, Any]],
) -> MLPrompt:
    system_prompt = (
        "You are a production incident response copilot. "
        "Provide concise, actionable guidance. "
        "Do not restate the user prompt. "
        "Use the observability context as the source of truth and do not invent metrics/logs. "
        "If observability context is present, do not ask the user to provide those results. "
        "If the user requests an exact code change, respond with a minimal unified diff "
        "inside a ```diff code block. "
        "If information is missing, ask 1-2 targeted follow-up questions."
    )
    context_payload = json.dumps(context, indent=2) if context else "No incident context provided."
    summary_payload = summary or "No conversation summary yet."
    user_prompt = (
        "User request:\n"
        f"{question}\n\n"
        "Incident context:\n"
        f"{context_payload}\n\n"
        "Conversation summary:\n"
        f"{summary_payload}\n\n"
        "Recent conversation:\n"
        f"{history_text}\n\n"
        "Observability context:\n"
        f"{json.dumps(observability, indent=2) if observability else 'No observability context.'}\n"
    )
    return MLPrompt(system_prompt=system_prompt, user_prompt=user_prompt)


def _extract_copilot_text(result: Any) -> str:
    if isinstance(result, dict):
        if "raw_response" in result and len(result) == 1:
            return str(result["raw_response"])
        if "error" in result:
            return f"Copilot error: {result['error']}"
        return json.dumps(result, indent=2)
    return str(result)


async def _run_copilot(
    question: str,
    context: Dict[str, Any],
    summary: Optional[str],
    history_text: str,
    observability: Optional[Dict[str, Any]],
) -> Any:
    router = ModelRouter()
    provider = router.select(MLTaskType.root_cause_analysis)
    prompt = _build_copilot_prompt(question, context, summary, history_text, observability)
    response = await provider.generate(prompt)
    response.task = MLTaskType.root_cause_analysis
    return response.result


def _extract_prom_value(result: Dict[str, Any]) -> Optional[str]:
    try:
        data = result.get("data", {})
        series = data.get("result", [])
        if series and "value" in series[0]:
            return series[0]["value"][1]
    except Exception:
        return None
    return None


def _format_observability_summary(observability: Optional[Dict[str, Any]]) -> Optional[str]:
    if not observability:
        return None
    lines = []
    service = observability.get("service")
    if service:
        lines.append(f"Service: {service}")
    prom = observability.get("prometheus")
    if isinstance(prom, dict):
        lines.append("Prometheus: up/error_rate/p95_latency fetched")
    prom_queries = observability.get("prometheus_queries")
    if isinstance(prom_queries, list):
        for item in prom_queries:
            if not isinstance(item, dict):
                continue
            lines.append(f"PromQL query: {item.get('query')}")
            value = _extract_prom_value(item.get("result") or {})
            if value is not None:
                lines.append(f"PromQL value: {value}")
    if observability.get("prometheus_error"):
        lines.append(f"Prometheus error: {observability['prometheus_error']}")
    loki_logs = observability.get("loki_logs")
    if isinstance(loki_logs, list) and loki_logs:
        lines.append("Loki logs:")
        lines.extend([f"- {line}" for line in loki_logs])
    loki_queries = observability.get("loki_queries")
    if isinstance(loki_queries, list):
        for item in loki_queries:
            if not isinstance(item, dict):
                continue
            lines.append(f"Loki query: {item.get('query')}")
            logs = item.get("logs") or []
            if logs:
                lines.append("Loki query logs:")
                lines.extend([f"- {line}" for line in logs])
    if observability.get("loki_error"):
        lines.append(f"Loki error: {observability['loki_error']}")
    grafana = observability.get("grafana", {})
    dashboards = grafana.get("dashboards") if isinstance(grafana, dict) else None
    if isinstance(dashboards, dict) and dashboards:
        lines.append("Grafana dashboards:")
        for name, url in dashboards.items():
            lines.append(f"- {name}: {url}")
    if observability.get("grafana_error"):
        lines.append(f"Grafana error: {observability['grafana_error']}")
    return "\n".join(lines) if lines else None


def _should_fetch_observability(question: str) -> bool:
    question_lower = question.lower()
    keywords = (
        "grafana",
        "dashboard",
        "prometheus",
        "loki",
        "logs",
        "metrics",
        "traces",
        "telemetry",
        "promql:",
        "loki:",
        "grafana:",
        "logs:",
        "metrics:",
        "dash:",
        "check:",
        "runbook:",
    )
    return any(keyword in question_lower for keyword in keywords)


def _extract_service_name(context: Dict[str, Any]) -> str:
    labels = context.get("labels") or {}
    return labels.get("service") or labels.get("app") or "incident-api"


def _simplify_loki_result(result: Dict[str, Any], max_lines: int = 5) -> list[str]:
    lines: list[str] = []
    data = result.get("data", {})
    for stream in data.get("result", [])[:3]:
        for _, line in stream.get("values", [])[:max_lines]:
            lines.append(line)
            if len(lines) >= max_lines:
                return lines
    return lines


def _parse_incident_id(question: str) -> Optional[UUID]:
    match = re.search(r"\b([0-9a-fA-F-]{36})\b", question)
    if not match:
        return None
    try:
        return UUID(match.group(1))
    except ValueError:
        return None


def _parse_stage_command(question: str) -> Optional[str]:
    match = re.search(r"\b(stage|status):\s*([a-z_-]+)\b", question, re.IGNORECASE)
    if match:
        return match.group(2).lower()
    if re.search(r"\bclose ticket\b|\bclose issue\b|\bresolve incident\b", question, re.IGNORECASE):
        return "closed"
    return None


def _normalize_stage(stage: str) -> str:
    mapping = {
        "triage": "new",
        "investigating": "investigating",
        "identified": "identified",
        "mitigating": "monitoring",
        "monitoring": "monitoring",
        "resolved": "resolved",
        "closed": "closed",
        "close": "closed",
    }
    return mapping.get(stage, stage)


def _stage_label(stage: str) -> str:
    return f"stage:{stage}"


async def _update_incident_stage(session: AsyncSession, incident_id: UUID, stage: str) -> None:
    incident = await IncidentRepository(session).get(incident_id)
    if not incident:
        return
    normalized = _normalize_stage(stage)
    if hasattr(incident, "status"):
        incident.status = normalized
    if normalized in {"resolved", "closed"}:
        incident.resolved_at = incident.resolved_at or datetime.utcnow()
        if normalized == "closed":
            incident.closed_at = incident.closed_at or datetime.utcnow()
    await session.flush()


def _append_timeline(extra_data: Dict[str, Any], entry: str) -> Dict[str, Any]:
    timeline = list(extra_data.get("timeline", []))
    timeline.append(entry)
    extra_data["timeline"] = timeline[-20:]
    return extra_data


def _append_exchange(extra_data: Dict[str, Any], user_message: str, assistant_message: str) -> Dict[str, Any]:
    timestamp = datetime.now(timezone.utc).isoformat()
    entry = f"{timestamp} user='{user_message[:120]}' copilot='{assistant_message[:120]}'"
    return _append_timeline(extra_data, entry)


def _build_incident_report(
    context: Dict[str, Any],
    summary: Dict[str, Any] | str,
    timeline: Optional[list[str]],
    observability_summary: Optional[str],
) -> str:
    lines = ["Incident Response Report"]
    incident_id = context.get("id", "unknown")
    title = context.get("title", "Unknown incident")
    severity = str(context.get("severity", "unknown"))
    category = str(context.get("category", "unknown"))
    lines.append(f"Incident: {title} ({incident_id})")
    lines.append(f"Severity: {severity} | Category: {category}")
    lines.append("")
    lines.append("Summary:")
    lines.extend(_format_summary_lines(summary))
    lines.append("")
    if observability_summary:
        lines.append("Observability Summary:")
        lines.append(observability_summary)
        lines.append("")
    if timeline:
        lines.append("Timeline:")
        for entry in timeline[-10:]:
            lines.append(f"- {entry}")
        lines.append("")
    lines.append("Status: resolved")
    return "\n".join(lines)


async def _apply_ticket_stage(
    session: AsyncSession,
    stage: str,
    metadata: Dict[str, Any],
) -> None:
    config = load_integrations_config()
    jira_cfg = config.get("incident_management", {}).get("jira", {})
    github_cfg = config.get("version_control", {}).get("github", {})

    # Jira transition (best-effort)
    jira_key = metadata.get("jira_ticket_key")
    if jira_key and jira_cfg.get("enabled") and jira_cfg.get("url"):
        transition_name = stage.replace("_", " ").title()
        jira = JiraIntegration(
            url=jira_cfg.get("url"),
            username=jira_cfg.get("username"),
            api_token=jira_cfg.get("api_token"),
            project_key=jira_cfg.get("project_key", "INC"),
            issue_type=jira_cfg.get("issue_type", "Bug"),
        )
        try:
            await jira.transition_ticket(ticket_key=jira_key, transition_name=transition_name)
        except Exception:
            pass
        finally:
            await jira.close()

    # GitHub labels/close (best-effort)
    issue_number = metadata.get("github_issue_number")
    if issue_number and github_cfg.get("enabled") and github_cfg.get("token") and github_cfg.get("repository"):
        github = GitHubIntegration(
            token=github_cfg.get("token"),
            repository=github_cfg.get("repository"),
        )
        try:
            await github.add_labels(int(issue_number), [_stage_label(stage)])
            if stage in {"resolved", "closed"}:
                await github.close_issue(int(issue_number), comment=f"Incident marked {stage}.")
        except Exception:
            pass
        finally:
            await github.close()


def _extract_inline_queries(question: str, prefix: str) -> list[str]:
    pattern = rf"{prefix}:\s*([^\n]+)"
    matches = re.findall(pattern, question, re.IGNORECASE)
    queries: list[str] = []
    for raw in matches:
        query = raw.strip()
        if len(query) > MAX_QUERY_LENGTH:
            query = query[:MAX_QUERY_LENGTH]
        if query:
            queries.append(query)
    return queries


def _extract_time_range(question: str) -> Optional[int]:
    match = re.search(r"time_range\s*=\s*(\d+)([smhd])", question, re.IGNORECASE)
    if not match:
        return None
    value = int(match.group(1))
    unit = match.group(2).lower()
    multiplier = {"s": 1, "m": 60, "h": 3600, "d": 86400}
    return value * multiplier[unit]


def _derive_check_queries(question: str, service: str) -> tuple[list[str], list[str]]:
    checks = []
    for token in re.findall(r"(check|runbook):\s*([^\n]+)", question, re.IGNORECASE):
        checks.append(token[1].strip().lower())

    prom_queries: list[str] = []
    loki_queries: list[str] = []
    for check in checks:
        if "504" in check or "timeout" in check:
            prom_queries.append(
                f'sum(rate(http_requests_total{{job="{service}",status="504"}}[5m]))'
            )
            prom_queries.append(
                f'histogram_quantile(0.95, sum(rate(http_request_duration_seconds_bucket{{job="{service}"}}[5m])) by (le))'
            )
            loki_queries.append(f'{{service="{service}"}} |~ "(?i)timeout|gateway|504"')
        if "400" in check or "validation" in check or "bad request" in check:
            prom_queries.append(
                f'sum(rate(http_requests_total{{job="{service}",status="400"}}[5m]))'
            )
            loki_queries.append(f'{{service="{service}"}} |~ "(?i)validation|bad request|400"')
        if "latency" in check:
            prom_queries.append(
                f'histogram_quantile(0.95, sum(rate(http_request_duration_seconds_bucket{{job="{service}"}}[5m])) by (le))'
            )
        if "db" in check or "database" in check:
            loki_queries.append(f'{{service="{service}"}} |~ "(?i)db|database|pool|connection"')
    return prom_queries, loki_queries


def _search_code_snippets(query: str) -> list[dict[str, Any]]:
    if not query:
        return []
    results: list[dict[str, Any]] = []
    for root, _, files in os.walk(CODE_ROOT):
        for filename in files:
            if not filename.endswith(".py"):
                continue
            path = os.path.join(root, filename)
            try:
                with open(path, "r", encoding="utf-8") as handle:
                    lines = handle.readlines()
            except Exception:
                continue
            for idx, line in enumerate(lines):
                if query.lower() in line.lower():
                    start = max(idx - 2, 0)
                    end = min(idx + 3, len(lines))
                    snippet = "".join(lines[start:end])
                    results.append(
                        {
                            "file": path.replace(CODE_ROOT, "src"),
                            "line": idx + 1,
                            "snippet": snippet.strip(),
                        }
                    )
                    break
            if len(results) >= MAX_CODE_RESULTS:
                return results
    return results


async def _build_context_pack(session: AsyncSession) -> Dict[str, Any]:
    context_pack: Dict[str, Any] = {"generated_at": datetime.now(timezone.utc).isoformat()}

    incident_rows = await session.execute(
        select(Incident).order_by(Incident.created_at.desc()).limit(MAX_CONTEXT_INCIDENTS)
    )
    incidents = incident_rows.scalars().all()
    context_pack["recent_incidents"] = [
        {
            "id": str(item.id),
            "title": item.title,
            "severity": str(item.severity),
            "category": str(item.category),
            "status": str(item.status),
            "created_at": item.created_at.isoformat(),
        }
        for item in incidents
    ]

    alert_rows = await session.execute(
        select(Alert).order_by(Alert.created_at.desc()).limit(MAX_CONTEXT_ALERTS)
    )
    alerts = alert_rows.scalars().all()
    context_pack["recent_alerts"] = [
        {
            "id": str(item.id),
            "severity": item.severity,
            "status": item.status,
            "message": item.message,
            "source": item.source,
            "created_at": item.created_at.isoformat(),
        }
        for item in alerts
    ]
    return context_pack


async def _fetch_observability_context(
    question: str,
    context: Dict[str, Any],
) -> Dict[str, Any]:
    if not _should_fetch_observability(question):
        return {}

    config = load_integrations_config()
    service = _extract_service_name(context)
    observability: Dict[str, Any] = {"service": service}

    prom_queries = _extract_inline_queries(question, "promql")
    prom_queries.extend(_extract_inline_queries(question, "metrics"))
    loki_queries = _extract_inline_queries(question, "loki")
    loki_queries.extend(_extract_inline_queries(question, "logs"))
    grafana_queries = _extract_inline_queries(question, "grafana")
    grafana_queries.extend(_extract_inline_queries(question, "dash"))
    range_seconds = _extract_time_range(question) or 900

    derived_prom, derived_loki = _derive_check_queries(question, service)
    prom_queries.extend(derived_prom)
    loki_queries.extend(derived_loki)

    # Prometheus summary or explicit query
    prom_cfg = config.get("observability", {}).get("prometheus", {})
    if prom_cfg.get("enabled"):
        prom = PrometheusIntegration({"base_url": prom_cfg.get("url")})
        try:
            if prom_queries:
                results = []
                for query in prom_queries[:MAX_PROM_SERIES]:
                    results.append(
                        {
                            "query": query,
                            "result": await prom.query(query),
                        }
                    )
                observability["prometheus_queries"] = results
            else:
                observability["prometheus"] = {
                    "up": await prom.query(f'up{{job="{service}"}}'),
                    "error_rate": await prom.query(
                        f'sum(rate(http_requests_total{{job="{service}",status=~"5.."}}[5m])) '
                        f'/ sum(rate(http_requests_total{{job="{service}"}}[5m]))'
                    ),
                    "p95_latency": await prom.query(
                        f'histogram_quantile(0.95, sum(rate(http_request_duration_seconds_bucket{{job="{service}"}}[5m])) by (le))'
                    ),
                }
        except Exception as exc:
            observability["prometheus_error"] = str(exc)

    # Loki summary or explicit query
    loki_cfg = config.get("observability", {}).get("loki", {})
    if loki_cfg.get("enabled"):
        loki = LokiIntegration({"base_url": loki_cfg.get("url")})
        try:
            if loki_queries:
                results = []
                for query in loki_queries[:MAX_PROM_SERIES]:
                    logs = await loki.query(
                        query,
                        limit=MAX_LOG_LINES,
                        range_seconds=range_seconds,
                    )
                    results.append(
                        {
                            "query": query,
                            "logs": _simplify_loki_result(logs, max_lines=MAX_LOG_LINES),
                        }
                    )
                observability["loki_queries"] = results
            else:
                logs = await loki.query(
                    f'{{service="{service}"}} |~ "(?i)error|exception|fail"'
                )
                observability["loki_logs"] = _simplify_loki_result(logs)
        except Exception as exc:
            observability["loki_error"] = str(exc)

    # Grafana dashboard links or explicit dashboard UID
    grafana_cfg = config.get("observability", {}).get("grafana", {})
    grafana_url = grafana_cfg.get("url")
    if grafana_cfg.get("enabled") and grafana_url:
        dashboards = grafana_cfg.get("dashboards", {})
        if grafana_queries:
            dashboards = {f"custom_{i+1}": uid for i, uid in enumerate(grafana_queries)}
        observability["grafana"] = {
            "base_url": grafana_url,
            "dashboards": {
                name: f"{grafana_url}/d/{uid}" for name, uid in dashboards.items() if uid
            },
        }
        # Optional: fetch dashboard metadata if API key is present
        api_key = grafana_cfg.get("auth", {}).get("token")
        if api_key and dashboards:
            graf = GrafanaIntegration({"base_url": grafana_url, "api_key": api_key})
            try:
                first_uid = next(iter(dashboards.values()))
                observability["grafana_sample"] = await graf.get_dashboard(first_uid)
            except Exception as exc:
                observability["grafana_error"] = str(exc)

    return observability


def _maybe_attach_code_context(question: str) -> Optional[Dict[str, Any]]:
    query = None
    for prefix in ("code", "search"):
        matches = _extract_inline_queries(question, prefix)
        if matches:
            query = matches[0]
            break
    if not query:
        return None
    return {"query": query, "matches": _search_code_snippets(query)}


async def _summarize_conversation(
    previous_summary: Optional[str],
    user_message: str,
    assistant_message: str,
    context: Dict[str, Any],
) -> Dict[str, Any] | str:
    system_prompt = (
        "You summarize incident response conversations. "
        "Return JSON with fields: user_intent, steps_tried, findings, next_actions, open_questions. "
        "Each field should be a short string or list of short strings."
    )
    context_payload = json.dumps(context, indent=2) if context else "No incident context provided."
    user_prompt = (
        "Previous summary:\n"
        f"{previous_summary or 'None'}\n\n"
        "Latest exchange:\n"
        f"User: {user_message}\n"
        f"Copilot: {assistant_message}\n\n"
        "Incident context:\n"
        f"{context_payload}\n"
    )
    router = ModelRouter()
    provider = router.select(MLTaskType.root_cause_analysis)
    prompt = MLPrompt(system_prompt=system_prompt, user_prompt=user_prompt)
    response = await provider.generate(prompt)
    response.task = MLTaskType.root_cause_analysis
    result = response.result
    if isinstance(result, dict):
        return result
    try:
        return json.loads(str(result))
    except json.JSONDecodeError:
        return str(result)


def _format_summary_lines(summary: Dict[str, Any] | str) -> list[str]:
    if isinstance(summary, dict):
        lines = []
        for key in ["user_intent", "steps_tried", "findings", "next_actions", "open_questions"]:
            value = summary.get(key)
            if not value:
                continue
            if isinstance(value, list):
                lines.append(f"{key.replace('_', ' ').title()}: " + "; ".join(str(v) for v in value))
            else:
                lines.append(f"{key.replace('_', ' ').title()}: {value}")
        return lines
    return [str(summary)]


def _build_ticket_comment(
    summary: Dict[str, Any] | str,
    user_message: str,
    assistant_message: str,
    context: Dict[str, Any],
    stage: str,
    timeline: Optional[list[str]] = None,
) -> str:
    timestamp = datetime.now(timezone.utc).isoformat()
    lines = ["Copilot Conversation Update"]
    lines.append(f"Timestamp: {timestamp}")
    lines.append(f"Stage: {stage}")
    if context:
        title = context.get("title") or "Unknown incident"
        incident_id = context.get("id") or "unknown"
        severity = context.get("severity") or "unknown"
        lines.append(f"Incident: {title} ({incident_id})")
        lines.append(f"Severity: {severity}")
    lines.append("")
    lines.extend(_format_summary_lines(summary))
    lines.append("")
    if timeline:
        lines.append("Timeline (recent):")
        for entry in timeline[-5:]:
            lines.append(f"- {entry}")
        lines.append("")
    lines.append("Latest exchange:")
    lines.append(f"- User: {user_message}")
    lines.append(f"- Copilot: {assistant_message}")
    return "\n".join(lines)


async def _update_tickets(
    session: AsyncSession,
    conversation,
    context: Dict[str, Any],
    summary: Dict[str, Any] | str,
    user_message: str,
    assistant_message: str,
) -> None:
    config = load_integrations_config()
    metadata = conversation.extra_data or {}
    stage = metadata.get("stage", DEFAULT_STAGE)
    timeline = metadata.get("timeline", [])

    comment_body = _build_ticket_comment(
        summary,
        user_message,
        assistant_message,
        context,
        stage=stage,
        timeline=timeline,
    )

    jira_cfg = config.get("incident_management", {}).get("jira", {})
    github_cfg = config.get("version_control", {}).get("github", {})

    if jira_cfg.get("enabled") and jira_cfg.get("url") and jira_cfg.get("username") and jira_cfg.get("api_token"):
        jira_key = metadata.get("jira_ticket_key")
        jira = JiraIntegration(
            url=jira_cfg.get("url"),
            username=jira_cfg.get("username"),
            api_token=jira_cfg.get("api_token"),
            project_key=jira_cfg.get("project_key", "INC"),
            issue_type=jira_cfg.get("issue_type", "Bug"),
        )
        try:
            if not jira_key:
                summary_title = context.get("title") or "Copilot conversation"
                description = comment_body
                created = await jira.create_ticket(
                    summary=summary_title,
                    description=description,
                    incident_id=context.get("id"),
                )
                jira_key = created.get("key")
                metadata.update(
                    {
                        "jira_ticket_key": created.get("key"),
                        "jira_ticket_url": created.get("url"),
                    }
                )
            else:
                await jira.add_comment(ticket_key=jira_key, comment=comment_body)
            record_copilot_ticket_update("jira", "success")
        except Exception:
            record_copilot_ticket_update("jira", "error")
        finally:
            await jira.close()

    if github_cfg.get("enabled") and github_cfg.get("token") and github_cfg.get("repository"):
        issue_number = metadata.get("github_issue_number")
        github = GitHubIntegration(
            token=github_cfg.get("token"),
            repository=github_cfg.get("repository"),
        )
        try:
            if not issue_number:
                issue_title = context.get("title") or "Copilot conversation"
                created = await github.create_issue(
                    title=issue_title,
                    body=comment_body,
                    incident_id=context.get("id"),
                )
                issue_number = created.get("number")
                metadata.update(
                    {
                        "github_issue_number": created.get("number"),
                        "github_issue_url": created.get("url"),
                    }
                )
            else:
                await github.add_comment(issue_number=int(issue_number), body=comment_body)
            record_copilot_ticket_update("github", "success")
        except Exception:
            record_copilot_ticket_update("github", "error")
        finally:
            await github.close()

    repo = CopilotConversationRepository(session)
    await repo.update_metadata(conversation, metadata)


@router.post("/chat", response_model=CopilotChatResponse)
async def copilot_chat(
    payload: CopilotChatRequest,
    session: AsyncSession = Depends(get_db_session),
):
    if not payload.incident_id:
        raise HTTPException(
            status_code=400,
            detail="incident_id is required for Copilot conversations",
        )
    context = await _incident_context(session, payload.incident_id)
    source = payload.source or "api"
    repo = CopilotConversationRepository(session)
    conversation = await repo.get_or_create(
        incident_id=payload.incident_id,
        user_id=payload.user_id,
        channel_id=payload.channel_id,
        source=source,
        metadata={"source": source},
    )
    history_messages = await repo.list_recent_messages(conversation.id, limit=MAX_HISTORY_MESSAGES)
    history_text = _format_history(history_messages)
    observability = await _fetch_observability_context(payload.prompt, context)
    context_pack = await _build_context_pack(session)
    code_context = _maybe_attach_code_context(payload.prompt)
    if code_context:
        context_pack["code_lookup"] = code_context

    stage_command = _parse_stage_command(payload.prompt or "")
    if stage_command and payload.incident_id:
        if context.get("status") in {"resolved", "closed"} and _normalize_stage(stage_command) in {"resolved", "closed"}:
            report = (conversation.extra_data or {}).get("last_report")
            if not report:
                report = _build_incident_report(
                    context=context,
                    summary=summary_result if "summary_result" in locals() else "No summary available.",
                    timeline=(conversation.extra_data or {}).get("timeline", []),
                    observability_summary=None,
                )
            return CopilotChatResponse(
                status="ok",
                response={
                    "text": "Incident is already resolved.",
                    "report": report,
                },
            )
        normalized_stage = _normalize_stage(stage_command)
        await _update_incident_stage(session, payload.incident_id, normalized_stage)
        metadata = conversation.extra_data or {}
        metadata["stage"] = normalized_stage
        entry = f"{datetime.now(timezone.utc).isoformat()} stage set to {normalized_stage}"
        metadata = _append_timeline(metadata, entry)
        await _apply_ticket_stage(session, normalized_stage, metadata)
        await repo.update_metadata(conversation, metadata)

    result = await _run_copilot(
        payload.prompt,
        {**context, "context_pack": context_pack},
        conversation.latest_summary,
        history_text,
        observability,
    )
    assistant_text = _extract_copilot_text(result)
    observability_summary = _format_observability_summary(observability)

    await repo.append_message(conversation, "user", payload.prompt, {"source": source})
    record_copilot_message(source, "user")
    await repo.append_message(conversation, "assistant", assistant_text, {"source": source})
    record_copilot_message(source, "assistant")

    summary_result = await _summarize_conversation(
        previous_summary=conversation.latest_summary,
        user_message=payload.prompt,
        assistant_message=assistant_text,
        context=context,
    )
    summary_text = (
        json.dumps(summary_result, indent=2) if isinstance(summary_result, dict) else str(summary_result)
    )
    await repo.update_summary(conversation, summary_text)

    metadata = conversation.extra_data or {}
    messages_since = int(metadata.get("messages_since_ticket_update", 0)) + 1
    metadata["messages_since_ticket_update"] = messages_since
    metadata = _append_exchange(metadata, payload.prompt, assistant_text)
    await repo.update_metadata(conversation, metadata)

    force_update = bool(re.search(r"\bupdate ticket\b", payload.prompt, re.IGNORECASE))
    if messages_since >= TICKET_UPDATE_EVERY or force_update:
        await _update_tickets(session, conversation, context, summary_result, payload.prompt, assistant_text)
        await repo.update_metadata(conversation, {"messages_since_ticket_update": 0})

    response_payload: Dict[str, Any] = {"text": assistant_text, "raw": result}
    if observability_summary:
        response_payload["observability"] = observability_summary
    stage = (conversation.extra_data or {}).get("stage")
    if stage in {"resolved", "closed"}:
        report = _build_incident_report(
            context=context,
            summary=summary_result,
            timeline=(conversation.extra_data or {}).get("timeline", []),
            observability_summary=observability_summary,
        )
        metadata = conversation.extra_data or {}
        metadata["last_report"] = report
        await repo.update_metadata(conversation, metadata)
        response_payload["report"] = report
        await _update_tickets(session, conversation, context, summary_result, payload.prompt, assistant_text)
    return CopilotChatResponse(
        status="ok",
        response=response_payload,
    )


SLACK_CMD_PATTERN = re.compile(r"^(?P<incident>[0-9a-fA-F-]{36})\s+(?P<question>.+)$")


async def _process_slack_copilot(
    response_url: str,
    text: str,
    user_id: Optional[str],
    channel_id: Optional[str],
    team_id: Optional[str],
) -> None:
    import httpx

    try:
        incident_id = None
        question = text.strip()
        match = SLACK_CMD_PATTERN.match(question)
        if match:
            try:
                incident_id = UUID(match.group("incident"))
                question = match.group("question").strip()
            except ValueError:
                incident_id = None

        async with get_db_session_context() as session:
            repo = CopilotConversationRepository(session)
            # If no incident id provided, reuse bound incident from conversation metadata.
            if incident_id is None:
                existing = await repo.get_by_identity(None, user_id, channel_id, "slack")
                if existing and existing.extra_data and existing.extra_data.get("incident_id"):
                    try:
                        incident_id = UUID(existing.extra_data["incident_id"])
                    except Exception:
                        incident_id = None

            if incident_id is None:
                async with httpx.AsyncClient() as client:
                    await client.post(
                        response_url,
                        json={
                            "response_type": "ephemeral",
                            "text": "Please provide an incident ID: `/copilot <incident-uuid> <message>`",
                        },
                        timeout=10,
                    )
                return

            context = await _incident_context(session, incident_id)
            repo = CopilotConversationRepository(session)
            conversation = await repo.get_or_create(
                incident_id=incident_id,
                user_id=user_id,
                channel_id=channel_id,
                source="slack",
                metadata={"source": "slack", "team_id": team_id},
            )
            if incident_id:
                await repo.update_metadata(conversation, {"incident_id": str(incident_id)})
            history_messages = await repo.list_recent_messages(
                conversation.id,
                limit=MAX_HISTORY_MESSAGES,
            )
            history_text = _format_history(history_messages)
            observability = await _fetch_observability_context(question, context)
            context_pack = await _build_context_pack(session)
            code_context = _maybe_attach_code_context(question)
            if code_context:
                context_pack["code_lookup"] = code_context

            stage_command = _parse_stage_command(question or "")
            if stage_command and incident_id:
                if context.get("status") in {"resolved", "closed"} and _normalize_stage(stage_command) in {"resolved", "closed"}:
                    report = (conversation.extra_data or {}).get("last_report")
                    if not report:
                        report = _build_incident_report(
                            context=context,
                            summary="No summary available.",
                            timeline=(conversation.extra_data or {}).get("timeline", []),
                            observability_summary=None,
                        )
                    message_text = "\n".join(
                        [
                            "*Copilot Analysis*",
                            f"Prompt: {question}",
                            "",
                            "Incident is already resolved.",
                            f"*Incident Report*:\n{report}",
                        ]
                    )
                    async with httpx.AsyncClient() as client:
                        await client.post(
                            response_url,
                            json={"response_type": "in_channel", "text": message_text},
                            timeout=30,
                        )
                    return
                normalized_stage = _normalize_stage(stage_command)
                await _update_incident_stage(session, incident_id, normalized_stage)
                metadata = conversation.extra_data or {}
                metadata["stage"] = normalized_stage
                metadata["incident_id"] = str(incident_id)
                entry = f"{datetime.now(timezone.utc).isoformat()} stage set to {normalized_stage}"
                metadata = _append_timeline(metadata, entry)
                await _apply_ticket_stage(session, normalized_stage, metadata)
                await repo.update_metadata(conversation, metadata)

            result = await _run_copilot(
                question,
                {**context, "context_pack": context_pack},
                conversation.latest_summary,
                history_text,
                observability,
            )
            assistant_text = _extract_copilot_text(result)
            observability_summary = _format_observability_summary(observability)

            await repo.append_message(
                conversation,
                "user",
                question,
                {"source": "slack", "user_id": user_id},
            )
            record_copilot_message("slack", "user")
            await repo.append_message(
                conversation,
                "assistant",
                assistant_text,
                {"source": "slack"},
            )
            record_copilot_message("slack", "assistant")

            summary_result = await _summarize_conversation(
                previous_summary=conversation.latest_summary,
                user_message=question,
                assistant_message=assistant_text,
                context=context,
            )
            summary_text = (
                json.dumps(summary_result, indent=2)
                if isinstance(summary_result, dict)
                else str(summary_result)
            )
            await repo.update_summary(conversation, summary_text)

            metadata = conversation.extra_data or {}
            messages_since = int(metadata.get("messages_since_ticket_update", 0)) + 1
            metadata["messages_since_ticket_update"] = messages_since
            metadata = _append_exchange(metadata, question, assistant_text)
            await repo.update_metadata(conversation, metadata)

            force_update = bool(re.search(r"\bupdate ticket\b", question, re.IGNORECASE))
            if messages_since >= TICKET_UPDATE_EVERY or force_update:
                await _update_tickets(session, conversation, context, summary_result, question, assistant_text)
                await repo.update_metadata(conversation, {"messages_since_ticket_update": 0})

        stage = (conversation.extra_data or {}).get("stage")
        if stage in {"resolved", "closed"}:
            report = _build_incident_report(
                context=context,
                summary=summary_result,
                timeline=(conversation.extra_data or {}).get("timeline", []),
                observability_summary=observability_summary,
            )
            metadata = conversation.extra_data or {}
            metadata["last_report"] = report
            await repo.update_metadata(conversation, metadata)
            await _update_tickets(session, conversation, context, summary_result, question, assistant_text)

        message_text = "\n".join(
            [
                "*Copilot Analysis*",
                f"Prompt: {question}",
                "",
                f"*Observability Summary*:\n{observability_summary}" if observability_summary else "",
                f"*Incident Report*:\n{report}" if stage in {"resolved", "closed"} else "",
                assistant_text,
            ]
        )

        async with httpx.AsyncClient() as client:
            resp = await client.post(
                response_url,
                json={"response_type": "in_channel", "text": message_text},
                timeout=30,
            )
            resp.raise_for_status()
            logger.info("Slack response sent: %s", resp.status_code)
    except Exception as exc:
        logger.exception("Slack copilot dispatch failed")
        async with httpx.AsyncClient() as client:
            await client.post(
                response_url,
                json={
                    "response_type": "ephemeral",
                    "text": f"Copilot failed to respond: {exc}",
                },
                timeout=10,
            )


@router.post("/slack/command")
async def copilot_slack_command(
    request: Request,
    background_tasks: BackgroundTasks,
    session: AsyncSession = Depends(get_db_session),
):
    # Slack sends form-encoded data
    form = await request.form()
    response_url = form.get("response_url")
    text = form.get("text", "")
    user_id = form.get("user_id")
    channel_id = form.get("channel_id")
    team_id = form.get("team_id")
    if not response_url:
        raise HTTPException(status_code=400, detail="Missing response_url")

    background_tasks.add_task(
        _process_slack_copilot,
        response_url,
        text,
        user_id,
        channel_id,
        team_id,
    )
    return {"response_type": "ephemeral", "text": "Copilot is analyzing your request..."}


@router.get("/demo", response_class=HTMLResponse)
async def copilot_demo_page() -> str:
    return """
<!doctype html>
<html>
  <head>
    <meta charset="utf-8" />
    <title>Copilot Demo</title>
    <style>
      body { font-family: Arial, sans-serif; padding: 24px; background: #0b0f14; color: #e6e6e6; }
      .card { max-width: 720px; margin: 0 auto; background: #121821; padding: 20px; border-radius: 8px; }
      input, textarea { width: 100%; margin: 8px 0 16px; padding: 10px; border-radius: 6px; border: 1px solid #2b3545; background: #0f1520; color: #e6e6e6; }
      button { padding: 10px 16px; border: 0; border-radius: 6px; background: #3b82f6; color: white; cursor: pointer; }
      pre { white-space: pre-wrap; background: #0f1520; padding: 12px; border-radius: 6px; }
    </style>
  </head>
  <body>
    <div class="card">
      <h2>Copilot Demo</h2>
      <label>Incident ID (optional)</label>
      <input id="incidentId" placeholder="UUID" />
      <label>Prompt</label>
      <textarea id="prompt" rows="6" placeholder="Describe the issue and what you want to troubleshoot"></textarea>
      <button onclick="send()">Ask Copilot</button>
      <h3>Response</h3>
      <pre id="out">Waiting...</pre>
    </div>
    <script>
      async function send() {
        const incident_id = document.getElementById('incidentId').value || null;
        const prompt = document.getElementById('prompt').value;
        const resp = await fetch('/copilot/chat', {
          method: 'POST',
          headers: {'Content-Type': 'application/json'},
          body: JSON.stringify({ prompt, incident_id })
        });
        const data = await resp.json();
        document.getElementById('out').textContent = JSON.stringify(data, null, 2);
      }
    </script>
  </body>
</html>
"""


@router.get("/local", response_class=HTMLResponse)
async def copilot_local_chat() -> str:
    return """
<!doctype html>
<html>
  <head>
    <meta charset="utf-8" />
    <title>Copilot Local Chat</title>
    <style>
      body { font-family: Arial, sans-serif; background: #0b0f14; color: #e6e6e6; margin: 0; }
      .container { max-width: 900px; margin: 0 auto; padding: 24px; }
      .header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 12px; }
      .panel { background: #121821; border-radius: 8px; padding: 16px; }
      .inputs { display: grid; grid-template-columns: 1fr 2fr auto; gap: 12px; align-items: end; }
      input, textarea { width: 100%; padding: 10px; border-radius: 6px; border: 1px solid #2b3545; background: #0f1520; color: #e6e6e6; }
      textarea { min-height: 90px; resize: vertical; }
      button { padding: 10px 16px; border: 0; border-radius: 6px; background: #3b82f6; color: white; cursor: pointer; }
      .chat { margin-top: 16px; display: flex; flex-direction: column; gap: 10px; }
      .bubble { padding: 12px 14px; border-radius: 8px; max-width: 80%; }
      .user { background: #1d2a3a; align-self: flex-end; }
      .assistant { background: #0f1520; align-self: flex-start; border: 1px solid #2b3545; }
      .meta { font-size: 12px; color: #9aa3af; margin-bottom: 6px; }
      pre { white-space: pre-wrap; margin: 0; }
    </style>
  </head>
  <body>
    <div class="container">
      <div class="header">
        <h2>Copilot Local Chat</h2>
        <small>POSTs to /copilot/chat</small>
      </div>
      <div class="panel">
        <div class="inputs">
          <div>
            <label>Incident ID (optional)</label>
            <input id="incidentId" placeholder="UUID" />
          </div>
          <div>
            <label>Prompt</label>
            <textarea id="prompt" placeholder="Describe the issue or ask for guidance"></textarea>
          </div>
          <div>
            <button onclick="send()">Send</button>
          </div>
        </div>
        <div class="chat" id="chat"></div>
      </div>
    </div>
    <script>
      const chat = document.getElementById('chat');
      function addBubble(role, text) {
        const wrap = document.createElement('div');
        wrap.className = 'bubble ' + role;
        const meta = document.createElement('div');
        meta.className = 'meta';
        meta.textContent = role === 'user' ? 'You' : 'Copilot';
        const body = document.createElement('pre');
        body.textContent = text;
        wrap.appendChild(meta);
        wrap.appendChild(body);
        chat.appendChild(wrap);
        chat.scrollTop = chat.scrollHeight;
      }
      async function send() {
        const incident_id = document.getElementById('incidentId').value || null;
        const prompt = document.getElementById('prompt').value;
        if (!prompt) return;
        addBubble('user', prompt);
        document.getElementById('prompt').value = '';
        const resp = await fetch('/copilot/chat', {
          method: 'POST',
          headers: {'Content-Type': 'application/json'},
          body: JSON.stringify({ prompt, incident_id })
        });
        const data = await resp.json();
        addBubble('assistant', JSON.stringify(data.response, null, 2));
      }
    </script>
  </body>
</html>
"""
