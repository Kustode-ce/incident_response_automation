"""Prometheus Metrics for Incident Response Automation."""

from __future__ import annotations

import logging
from typing import Optional

logger = logging.getLogger(__name__)

# Optional imports - only if prometheus_client is installed
try:
    from prometheus_client import (
        CONTENT_TYPE_LATEST,
        Counter,
        Gauge,
        Histogram,
        Info,
        generate_latest,
        REGISTRY,
    )
    PROMETHEUS_AVAILABLE = True
except ImportError:
    PROMETHEUS_AVAILABLE = False
    CONTENT_TYPE_LATEST = "text/plain"
    logger.warning("prometheus_client not installed. Metrics disabled.")

# =============================================================================
# API Metrics
# =============================================================================

if PROMETHEUS_AVAILABLE:
    # HTTP Request metrics
    HTTP_REQUESTS_TOTAL = Counter(
        "http_requests_total",
        "Total HTTP requests",
        ["method", "endpoint", "status"],
    )
    
    HTTP_REQUEST_DURATION = Histogram(
        "http_request_duration_seconds",
        "HTTP request duration in seconds",
        ["method", "endpoint"],
        buckets=(0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0),
    )
    
    HTTP_REQUESTS_IN_PROGRESS = Gauge(
        "http_requests_in_progress",
        "Number of HTTP requests currently being processed",
        ["method", "endpoint"],
    )

    # =============================================================================
    # Incident Metrics
    # =============================================================================
    
    INCIDENTS_CREATED_TOTAL = Counter(
        "incidents_created_total",
        "Total incidents created",
        ["severity", "category", "source"],
    )
    
    INCIDENTS_RESOLVED_TOTAL = Counter(
        "incidents_resolved_total",
        "Total incidents resolved",
        ["severity", "category"],
    )
    
    INCIDENT_RESOLUTION_TIME = Histogram(
        "incident_resolution_time_seconds",
        "Time to resolve incidents in seconds",
        ["severity", "category"],
        buckets=(60, 300, 600, 1800, 3600, 7200, 14400, 28800, 86400),
    )
    
    INCIDENTS_ACTIVE = Gauge(
        "incidents_active",
        "Number of currently active incidents",
        ["severity"],
    )

    # =============================================================================
    # Alert Metrics
    # =============================================================================
    
    ALERTS_RECEIVED_TOTAL = Counter(
        "alerts_received_total",
        "Total alerts received",
        ["source", "severity"],
    )
    
    ALERTS_PROCESSED_TOTAL = Counter(
        "alerts_processed_total",
        "Total alerts processed",
        ["source", "result"],
    )

    # =============================================================================
    # ML Metrics
    # =============================================================================
    
    ML_INFERENCE_TOTAL = Counter(
        "ml_inference_total",
        "Total ML inference requests",
        ["provider", "task", "status"],
    )
    
    ML_INFERENCE_DURATION = Histogram(
        "ml_inference_duration_seconds",
        "ML inference duration in seconds",
        ["provider", "task"],
        buckets=(0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0),
    )
    
    ML_TOKENS_USED = Counter(
        "ml_tokens_used_total",
        "Total tokens used for ML inference",
        ["provider", "type"],  # type: input/output
    )

    # =============================================================================
    # Integration Metrics
    # =============================================================================
    
    INTEGRATION_REQUESTS_TOTAL = Counter(
        "integration_requests_total",
        "Total integration requests",
        ["integration", "operation", "status"],
    )
    
    INTEGRATION_REQUEST_DURATION = Histogram(
        "integration_request_duration_seconds",
        "Integration request duration in seconds",
        ["integration", "operation"],
        buckets=(0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0),
    )

    # =============================================================================
    # Copilot Metrics
    # =============================================================================

    COPILOT_MESSAGES_TOTAL = Counter(
        "copilot_messages_total",
        "Total Copilot conversation messages",
        ["source", "role"],
    )

    COPILOT_TICKET_UPDATES_TOTAL = Counter(
        "copilot_ticket_updates_total",
        "Total Copilot ticket update attempts",
        ["integration", "status"],
    )

    # =============================================================================
    # SRE Monitoring Signals
    # =============================================================================

    SRE_SLO_BURN_RATE = Gauge(
        "sre_slo_burn_rate",
        "SLO error budget burn rate",
        ["service", "slo", "window"],
    )

    SRE_CANARY_HEALTH = Gauge(
        "sre_canary_health",
        "Canary health signal (1=healthy,0=unhealthy)",
        ["service"],
    )

    SRE_CANARY_TRAFFIC_SHARE = Gauge(
        "sre_canary_traffic_share",
        "Canary traffic share ratio",
        ["service"],
    )

    SRE_RECOVERY_READY = Gauge(
        "sre_recovery_ready",
        "Recovery readiness (1=ready,0=not ready)",
        ["service"],
    )

    SRE_RECOVERY_TESTS_TOTAL = Counter(
        "sre_recovery_tests_total",
        "Recovery readiness tests",
        ["service", "status"],
    )

    SRE_DEGRADED_MODE = Gauge(
        "sre_degraded_mode",
        "Degraded mode indicator (1=degraded,0=normal)",
        ["service", "reason"],
    )

    SRE_MITIGATION_RECOMMENDED = Gauge(
        "sre_mitigation_recommended",
        "Mitigation recommended flag (1=yes,0=no)",
        ["service", "action"],
    )

    SRE_DISK_PRESSURE = Gauge(
        "sre_disk_pressure",
        "Disk pressure indicator (1=pressure,0=normal)",
        ["service", "mount"],
    )

    # =============================================================================
    # Runbook Metrics
    # =============================================================================
    
    RUNBOOK_EXECUTIONS_TOTAL = Counter(
        "runbook_executions_total",
        "Total runbook executions",
        ["runbook", "status"],
    )
    
    RUNBOOK_EXECUTION_DURATION = Histogram(
        "runbook_execution_duration_seconds",
        "Runbook execution duration in seconds",
        ["runbook"],
        buckets=(1, 5, 10, 30, 60, 300, 600, 1800),
    )
    
    RUNBOOK_STEP_DURATION = Histogram(
        "runbook_step_duration_seconds",
        "Runbook step duration in seconds",
        ["runbook", "step"],
        buckets=(0.5, 1, 5, 10, 30, 60, 300),
    )

    # =============================================================================
    # Database Metrics
    # =============================================================================
    
    DB_CONNECTIONS_ACTIVE = Gauge(
        "db_connections_active",
        "Number of active database connections",
    )
    
    DB_QUERY_DURATION = Histogram(
        "db_query_duration_seconds",
        "Database query duration in seconds",
        ["operation"],
        buckets=(0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0),
    )

    # =============================================================================
    # Celery/Queue Metrics
    # =============================================================================
    
    CELERY_TASKS_TOTAL = Counter(
        "celery_tasks_total",
        "Total Celery tasks",
        ["task", "status"],
    )
    
    CELERY_TASK_DURATION = Histogram(
        "celery_task_duration_seconds",
        "Celery task duration in seconds",
        ["task"],
        buckets=(0.1, 0.5, 1.0, 5.0, 10.0, 30.0, 60.0, 300.0),
    )
    
    CELERY_QUEUE_LENGTH = Gauge(
        "celery_queue_length",
        "Number of tasks in Celery queue",
        ["queue"],
    )

    # =============================================================================
    # Application Info
    # =============================================================================
    
    APP_INFO = Info(
        "incident_response_app",
        "Application information",
    )

else:
    # Stub metrics when prometheus_client is not available
    HTTP_REQUESTS_TOTAL = None
    HTTP_REQUEST_DURATION = None
    HTTP_REQUESTS_IN_PROGRESS = None
    INCIDENTS_CREATED_TOTAL = None
    INCIDENTS_RESOLVED_TOTAL = None
    INCIDENT_RESOLUTION_TIME = None
    INCIDENTS_ACTIVE = None
    ALERTS_RECEIVED_TOTAL = None
    ALERTS_PROCESSED_TOTAL = None
    ML_INFERENCE_TOTAL = None
    ML_INFERENCE_DURATION = None
    ML_TOKENS_USED = None
    INTEGRATION_REQUESTS_TOTAL = None
    INTEGRATION_REQUEST_DURATION = None
    COPILOT_MESSAGES_TOTAL = None
    COPILOT_TICKET_UPDATES_TOTAL = None
    SRE_SLO_BURN_RATE = None
    SRE_CANARY_HEALTH = None
    SRE_CANARY_TRAFFIC_SHARE = None
    SRE_RECOVERY_READY = None
    SRE_RECOVERY_TESTS_TOTAL = None
    SRE_DEGRADED_MODE = None
    SRE_MITIGATION_RECOMMENDED = None
    SRE_DISK_PRESSURE = None
    RUNBOOK_EXECUTIONS_TOTAL = None
    RUNBOOK_EXECUTION_DURATION = None
    RUNBOOK_STEP_DURATION = None
    DB_CONNECTIONS_ACTIVE = None
    DB_QUERY_DURATION = None
    CELERY_TASKS_TOTAL = None
    CELERY_TASK_DURATION = None
    CELERY_QUEUE_LENGTH = None
    APP_INFO = None


def render_metrics() -> Optional[bytes]:
    """Generate Prometheus metrics in exposition format."""
    if not PROMETHEUS_AVAILABLE:
        return None
    return generate_latest()


def get_content_type() -> str:
    """Get the Prometheus metrics content type."""
    return CONTENT_TYPE_LATEST


def set_app_info(version: str, environment: str, **kwargs) -> None:
    """Set application info metric."""
    if APP_INFO:
        APP_INFO.info({
            "version": version,
            "environment": environment,
            **kwargs,
        })


# =============================================================================
# Metric Helper Functions
# =============================================================================

def record_http_request(method: str, endpoint: str, status: int, duration: float) -> None:
    """Record HTTP request metrics."""
    if HTTP_REQUESTS_TOTAL:
        HTTP_REQUESTS_TOTAL.labels(method=method, endpoint=endpoint, status=str(status)).inc()
    if HTTP_REQUEST_DURATION:
        HTTP_REQUEST_DURATION.labels(method=method, endpoint=endpoint).observe(duration)


def record_incident_created(severity: str, category: str, source: str) -> None:
    """Record incident creation metric."""
    if INCIDENTS_CREATED_TOTAL:
        INCIDENTS_CREATED_TOTAL.labels(
            severity=severity,
            category=category,
            source=source,
        ).inc()


def record_incident_resolved(severity: str, category: str, resolution_time: float) -> None:
    """Record incident resolution metric."""
    if INCIDENTS_RESOLVED_TOTAL:
        INCIDENTS_RESOLVED_TOTAL.labels(severity=severity, category=category).inc()
    if INCIDENT_RESOLUTION_TIME:
        INCIDENT_RESOLUTION_TIME.labels(severity=severity, category=category).observe(resolution_time)


def record_alert_received(source: str, severity: str) -> None:
    """Record alert received metric."""
    if ALERTS_RECEIVED_TOTAL:
        ALERTS_RECEIVED_TOTAL.labels(source=source, severity=severity).inc()


def record_ml_inference(provider: str, task: str, duration: float, status: str = "success",
                         input_tokens: int = 0, output_tokens: int = 0) -> None:
    """Record ML inference metric."""
    if ML_INFERENCE_TOTAL:
        ML_INFERENCE_TOTAL.labels(provider=provider, task=task, status=status).inc()
    if ML_INFERENCE_DURATION:
        ML_INFERENCE_DURATION.labels(provider=provider, task=task).observe(duration)
    if ML_TOKENS_USED and input_tokens:
        ML_TOKENS_USED.labels(provider=provider, type="input").inc(input_tokens)
    if ML_TOKENS_USED and output_tokens:
        ML_TOKENS_USED.labels(provider=provider, type="output").inc(output_tokens)


def record_integration_request(integration: str, operation: str, duration: float,
                                status: str = "success") -> None:
    """Record integration request metric."""
    if INTEGRATION_REQUESTS_TOTAL:
        INTEGRATION_REQUESTS_TOTAL.labels(
            integration=integration,
            operation=operation,
            status=status,
        ).inc()
    if INTEGRATION_REQUEST_DURATION:
        INTEGRATION_REQUEST_DURATION.labels(
            integration=integration,
            operation=operation,
        ).observe(duration)


def record_copilot_message(source: str, role: str) -> None:
    """Record Copilot message activity."""
    if COPILOT_MESSAGES_TOTAL:
        COPILOT_MESSAGES_TOTAL.labels(source=source, role=role).inc()


def record_copilot_ticket_update(integration: str, status: str) -> None:
    """Record Copilot ticket update attempts."""
    if COPILOT_TICKET_UPDATES_TOTAL:
        COPILOT_TICKET_UPDATES_TOTAL.labels(integration=integration, status=status).inc()


def record_sre_burn_rate(service: str, slo: str, window: str, value: float) -> None:
    """Record SLO burn rate."""
    if SRE_SLO_BURN_RATE:
        SRE_SLO_BURN_RATE.labels(service=service, slo=slo, window=window).set(value)


def record_sre_canary_health(service: str, healthy: bool, traffic_share: float) -> None:
    """Record canary health and traffic share."""
    if SRE_CANARY_HEALTH:
        SRE_CANARY_HEALTH.labels(service=service).set(1.0 if healthy else 0.0)
    if SRE_CANARY_TRAFFIC_SHARE:
        SRE_CANARY_TRAFFIC_SHARE.labels(service=service).set(traffic_share)


def record_sre_recovery_ready(service: str, ready: bool) -> None:
    """Record recovery readiness."""
    if SRE_RECOVERY_READY:
        SRE_RECOVERY_READY.labels(service=service).set(1.0 if ready else 0.0)


def record_sre_recovery_test(service: str, status: str) -> None:
    """Record recovery readiness tests."""
    if SRE_RECOVERY_TESTS_TOTAL:
        SRE_RECOVERY_TESTS_TOTAL.labels(service=service, status=status).inc()


def record_sre_degraded_mode(service: str, reason: str, degraded: bool) -> None:
    """Record degraded mode indicator."""
    if SRE_DEGRADED_MODE:
        SRE_DEGRADED_MODE.labels(service=service, reason=reason).set(1.0 if degraded else 0.0)


def record_sre_mitigation(service: str, action: str, recommended: bool) -> None:
    """Record mitigation recommendation."""
    if SRE_MITIGATION_RECOMMENDED:
        SRE_MITIGATION_RECOMMENDED.labels(service=service, action=action).set(
            1.0 if recommended else 0.0
        )


def record_sre_disk_pressure(service: str, mount: str, pressure: bool) -> None:
    """Record disk pressure indicator."""
    if SRE_DISK_PRESSURE:
        SRE_DISK_PRESSURE.labels(service=service, mount=mount).set(1.0 if pressure else 0.0)
