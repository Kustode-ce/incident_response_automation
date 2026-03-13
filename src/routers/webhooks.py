"""Webhook endpoints for receiving events from external systems."""

import hashlib
import hmac
import logging
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from src.services.alert_ingestion_service import AlertIngestionService
from src.utils.database import get_db_session

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/webhooks", tags=["Webhooks"])


# ==============================================
# Prometheus / AlertManager Webhooks
# ==============================================

class PrometheusAlert(BaseModel):
    status: str
    labels: Dict[str, str] = {}
    annotations: Dict[str, str] = {}
    startsAt: Optional[str] = None
    endsAt: Optional[str] = None
    generatorURL: Optional[str] = None
    fingerprint: Optional[str] = None


class PrometheusWebhook(BaseModel):
    status: str
    alerts: list[PrometheusAlert] = []
    groupLabels: Dict[str, str] = {}
    commonLabels: Dict[str, str] = {}
    commonAnnotations: Dict[str, str] = {}
    externalURL: Optional[str] = None
    groupKey: Optional[str] = None


@router.post("/prometheus")
async def prometheus_webhook(
    payload: PrometheusWebhook,
    session: AsyncSession = Depends(get_db_session),
):
    """Receive alerts from Prometheus AlertManager and create/update incidents."""
    logger.info(
        "Received Prometheus webhook: status=%s, alerts=%d",
        payload.status, len(payload.alerts),
    )

    raw_payload = {
        "status": payload.status,
        "alerts": [
            {
                "status": a.status,
                "labels": a.labels,
                "annotations": a.annotations,
                "startsAt": a.startsAt,
                "endsAt": a.endsAt,
            }
            for a in payload.alerts
        ],
    }

    service = AlertIngestionService(session)
    results = await service.ingest_alertmanager(raw_payload)

    created = sum(1 for r in results if r.get("status") == "created")
    deduped = sum(1 for r in results if r.get("status") == "deduplicated")
    resolved = sum(1 for r in results if r.get("status") == "resolved")

    _trigger_enrichment_for_new_incidents(results)

    return {
        "status": "accepted",
        "processed": len(results),
        "created": created,
        "deduplicated": deduped,
        "resolved": resolved,
        "details": results,
    }


@router.post("/alertmanager")
async def alertmanager_webhook(
    payload: PrometheusWebhook,
    session: AsyncSession = Depends(get_db_session),
):
    """Alias for Prometheus webhook (AlertManager uses same format)."""
    return await prometheus_webhook(payload, session)


def _trigger_enrichment_for_new_incidents(results: list[dict]) -> None:
    """Fire async enrichment tasks for newly created incidents."""
    try:
        from src.workers.tasks.enrichment import enrich_and_notify
    except ImportError:
        logger.debug("Celery enrichment tasks not available")
        return

    for r in results:
        if r.get("status") == "created" and r.get("incident_id"):
            try:
                enrich_and_notify.delay(r["incident_id"])
            except Exception:
                logger.warning("Could not enqueue enrichment for %s", r["incident_id"])


# ==============================================
# Grafana Webhooks
# ==============================================

class GrafanaWebhook(BaseModel):
    title: str
    state: str
    message: Optional[str] = None
    ruleId: Optional[int] = None
    ruleName: Optional[str] = None
    ruleUrl: Optional[str] = None
    evalMatches: list = []
    tags: Dict[str, str] = {}


@router.post("/grafana")
async def grafana_webhook(
    payload: GrafanaWebhook,
    session: AsyncSession = Depends(get_db_session),
):
    """Receive alert notifications from Grafana and create incidents."""
    logger.info("Received Grafana webhook: %s - %s", payload.title, payload.state)

    alert_status = "resolved" if payload.state == "ok" else "firing"
    normalized = {
        "status": alert_status,
        "alerts": [
            {
                "status": alert_status,
                "labels": {
                    "alertname": payload.ruleName or payload.title,
                    "source": "grafana",
                    **payload.tags,
                },
                "annotations": {
                    "summary": payload.title,
                    "description": payload.message or payload.title,
                    "rule_url": payload.ruleUrl or "",
                },
            }
        ],
    }

    service = AlertIngestionService(session)
    results = await service.ingest_alertmanager(normalized)

    _trigger_enrichment_for_new_incidents(results)

    return {"status": "accepted", "details": results}


# ==============================================
# Loki Webhooks
# ==============================================

@router.post("/loki")
async def loki_webhook(
    request: Request,
    session: AsyncSession = Depends(get_db_session),
):
    """Receive alert notifications from Loki and create incidents.

    Loki ruler uses the same webhook format as AlertManager.
    """
    payload = await request.json()
    logger.info("Received Loki webhook: status=%s", payload.get("status"))

    service = AlertIngestionService(session)
    results = await service.ingest_alertmanager(payload)

    _trigger_enrichment_for_new_incidents(results)

    return {"status": "accepted", "details": results}


# ==============================================
# Jira Webhooks
# ==============================================

# Jira webhook secret for verification
JIRA_WEBHOOK_SECRET = "885ueegKESUdr4DqzxKI"  # Move to env var in production


def verify_jira_signature(
    payload: bytes,
    signature: str,
    secret: str = JIRA_WEBHOOK_SECRET
) -> bool:
    """Verify Jira webhook signature."""
    if not signature or not secret:
        return True  # No verification if no secret
    
    expected = hmac.new(
        secret.encode(),
        payload,
        hashlib.sha256
    ).hexdigest()
    
    return hmac.compare_digest(f"sha256={expected}", signature)


class JiraIssueFields(BaseModel):
    summary: Optional[str] = None
    description: Optional[Any] = None
    priority: Optional[Dict[str, Any]] = None
    status: Optional[Dict[str, Any]] = None
    issuetype: Optional[Dict[str, Any]] = None
    project: Optional[Dict[str, Any]] = None
    labels: list[str] = []
    assignee: Optional[Dict[str, Any]] = None
    reporter: Optional[Dict[str, Any]] = None
    created: Optional[str] = None
    updated: Optional[str] = None


class JiraIssue(BaseModel):
    id: str
    key: str
    self: str
    fields: Optional[JiraIssueFields] = None


class JiraUser(BaseModel):
    accountId: Optional[str] = None
    displayName: Optional[str] = None
    emailAddress: Optional[str] = None


class JiraWebhookPayload(BaseModel):
    timestamp: Optional[int] = None
    webhookEvent: str
    issue_event_type_name: Optional[str] = None
    user: Optional[JiraUser] = None
    issue: Optional[JiraIssue] = None
    changelog: Optional[Dict[str, Any]] = None
    comment: Optional[Dict[str, Any]] = None


@router.post("/jira")
async def jira_webhook(
    request: Request,
    x_atlassian_webhook_identifier: Optional[str] = Header(None),
):
    """
    Receive webhooks from Jira.
    
    Configure in Jira:
    - URL: https://your-domain.com/webhooks/jira
    - Secret: 885ueegKESUdr4DqzxKI
    - Events: Issue created, updated, deleted (recommended)
    """
    # Get raw body for signature verification
    body = await request.body()
    
    # Parse payload
    try:
        payload_dict = await request.json()
        payload = JiraWebhookPayload(**payload_dict)
    except Exception as e:
        logger.error(f"Failed to parse Jira webhook: {e}")
        raise HTTPException(status_code=400, detail="Invalid payload")
    
    event_type = payload.webhookEvent
    logger.info(f"Received Jira webhook: event={event_type}")
    
    # Handle different event types
    if event_type == "jira:issue_created":
        return await handle_jira_issue_created(payload)
    elif event_type == "jira:issue_updated":
        return await handle_jira_issue_updated(payload)
    elif event_type == "jira:issue_deleted":
        return await handle_jira_issue_deleted(payload)
    elif event_type == "comment_created":
        return await handle_jira_comment(payload, "created")
    elif event_type == "comment_updated":
        return await handle_jira_comment(payload, "updated")
    else:
        logger.info(f"Unhandled Jira event: {event_type}")
        return {"status": "ignored", "event": event_type}


async def handle_jira_issue_created(payload: JiraWebhookPayload) -> Dict[str, Any]:
    """Handle Jira issue created event."""
    issue = payload.issue
    if not issue:
        return {"status": "ignored", "reason": "no issue in payload"}
    
    logger.info(f"Jira issue created: {issue.key}")
    
    # Check if this is an incident ticket
    issue_type = issue.fields.issuetype.get("name", "") if issue.fields and issue.fields.issuetype else ""
    labels = issue.fields.labels if issue.fields else []
    
    # If it's an incident-related ticket, we might want to create/link an incident
    if issue_type.lower() in ["incident", "bug", "problem"] or "incident" in [l.lower() for l in labels]:
        logger.info(f"Incident ticket detected: {issue.key}")
        # TODO: Create incident in our system and link to Jira ticket
    
    return {
        "status": "processed",
        "event": "issue_created",
        "issue_key": issue.key,
    }


async def handle_jira_issue_updated(payload: JiraWebhookPayload) -> Dict[str, Any]:
    """Handle Jira issue updated event."""
    issue = payload.issue
    changelog = payload.changelog
    
    if not issue:
        return {"status": "ignored", "reason": "no issue in payload"}
    
    logger.info(f"Jira issue updated: {issue.key}")
    
    # Check what changed
    changes = []
    if changelog and "items" in changelog:
        for item in changelog["items"]:
            field = item.get("field", "unknown")
            from_val = item.get("fromString", "")
            to_val = item.get("toString", "")
            changes.append(f"{field}: {from_val} -> {to_val}")
            logger.info(f"  Change: {field}: {from_val} -> {to_val}")
    
    # If status changed to "Done" or "Resolved", might want to update incident
    if changelog and "items" in changelog:
        for item in changelog["items"]:
            if item.get("field") == "status":
                new_status = item.get("toString", "").lower()
                if new_status in ["done", "resolved", "closed"]:
                    logger.info(f"Issue {issue.key} resolved, checking for linked incident")
                    # TODO: Update linked incident status
    
    return {
        "status": "processed",
        "event": "issue_updated",
        "issue_key": issue.key,
        "changes": changes,
    }


async def handle_jira_issue_deleted(payload: JiraWebhookPayload) -> Dict[str, Any]:
    """Handle Jira issue deleted event."""
    issue = payload.issue
    
    if not issue:
        return {"status": "ignored", "reason": "no issue in payload"}
    
    logger.info(f"Jira issue deleted: {issue.key}")
    
    # TODO: Update any linked incidents
    
    return {
        "status": "processed",
        "event": "issue_deleted",
        "issue_key": issue.key,
    }


async def handle_jira_comment(payload: JiraWebhookPayload, action: str) -> Dict[str, Any]:
    """Handle Jira comment events."""
    issue = payload.issue
    comment = payload.comment
    
    if not issue or not comment:
        return {"status": "ignored", "reason": "no issue or comment in payload"}
    
    comment_body = comment.get("body", "")
    author = comment.get("author", {}).get("displayName", "unknown")
    
    logger.info(f"Jira comment {action} on {issue.key} by {author}")
    
    # TODO: Sync comment to linked incident
    
    return {
        "status": "processed",
        "event": f"comment_{action}",
        "issue_key": issue.key,
    }


# ==============================================
# GitHub Webhooks
# ==============================================

GITHUB_WEBHOOK_SECRET = ""  # Set via env var


def verify_github_signature(
    payload: bytes,
    signature: str,
    secret: str = GITHUB_WEBHOOK_SECRET
) -> bool:
    """Verify GitHub webhook signature."""
    if not signature or not secret:
        return True
    
    expected = hmac.new(
        secret.encode(),
        payload,
        hashlib.sha256
    ).hexdigest()
    
    return hmac.compare_digest(f"sha256={expected}", signature)


@router.post("/github")
async def github_webhook(
    request: Request,
    x_github_event: Optional[str] = Header(None),
    x_hub_signature_256: Optional[str] = Header(None),
):
    """
    Receive webhooks from GitHub.
    
    Configure in GitHub:
    - URL: https://your-domain.com/webhooks/github
    - Content type: application/json
    - Events: Issues, Issue comments, Workflow runs
    """
    body = await request.body()
    
    # Verify signature if secret is configured
    if GITHUB_WEBHOOK_SECRET and not verify_github_signature(body, x_hub_signature_256 or ""):
        raise HTTPException(status_code=401, detail="Invalid signature")
    
    payload = await request.json()
    event = x_github_event or "unknown"
    
    logger.info(f"Received GitHub webhook: event={event}")
    
    if event == "issues":
        action = payload.get("action", "")
        issue = payload.get("issue", {})
        logger.info(f"GitHub issue {action}: #{issue.get('number')} - {issue.get('title')}")
        
        # If issue was closed, might want to update linked incident
        if action == "closed":
            # TODO: Update linked incident
            pass
    
    elif event == "issue_comment":
        action = payload.get("action", "")
        issue = payload.get("issue", {})
        comment = payload.get("comment", {})
        logger.info(f"GitHub comment {action} on #{issue.get('number')}")
        
        # TODO: Sync comment to linked incident
    
    elif event == "workflow_run":
        action = payload.get("action", "")
        workflow = payload.get("workflow_run", {})
        logger.info(f"GitHub workflow {action}: {workflow.get('name')} - {workflow.get('conclusion')}")
        
        # If deployment failed, might want to create incident
        if action == "completed" and workflow.get("conclusion") == "failure":
            # TODO: Create incident for failed deployment
            pass
    
    return {"status": "received", "event": event}


# ==============================================
# PagerDuty Webhooks
# ==============================================

@router.post("/pagerduty")
async def pagerduty_webhook(request: Request):
    """
    Receive webhooks from PagerDuty.
    
    Events: incident.triggered, incident.acknowledged, incident.resolved
    """
    payload = await request.json()
    
    messages = payload.get("messages", [])
    for message in messages:
        event_type = message.get("event", "unknown")
        incident = message.get("incident", {})
        
        logger.info(f"PagerDuty event: {event_type} - {incident.get('title', 'unknown')}")
        
        # Sync PagerDuty incident status with our system
        if event_type == "incident.triggered":
            # TODO: Create or link incident
            pass
        elif event_type == "incident.acknowledged":
            # TODO: Update incident status
            pass
        elif event_type == "incident.resolved":
            # TODO: Update incident status
            pass
    
    return {"status": "received"}


# ==============================================
# Slack Webhooks (for interactive messages)
# ==============================================

@router.post("/slack/interactive")
async def slack_interactive_webhook(request: Request):
    """
    Receive interactive message callbacks from Slack.
    
    Handles button clicks for approve/reject runbooks, etc.
    """
    # Slack sends form-encoded data
    form_data = await request.form()
    payload_str = form_data.get("payload", "{}")
    
    import json
    payload = json.loads(payload_str)
    
    action_type = payload.get("type", "")
    
    if action_type == "block_actions":
        actions = payload.get("actions", [])
        user = payload.get("user", {})
        
        for action in actions:
            action_id = action.get("action_id", "")
            value = action.get("value", "")
            
            logger.info(f"Slack action: {action_id} = {value} by {user.get('name')}")
            
            if action_id == "approve_runbook":
                # TODO: Approve runbook execution
                return {"text": "✅ Runbook approved!"}
            elif action_id == "reject_runbook":
                # TODO: Reject runbook execution
                return {"text": "❌ Runbook rejected."}
            elif action_id == "escalate":
                # TODO: Escalate incident
                return {"text": "📢 Incident escalated."}
    
    return {"status": "received"}
