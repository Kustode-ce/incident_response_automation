from .logging import configure_logging
from .metrics import (
    HTTP_REQUESTS_TOTAL,
    HTTP_REQUEST_DURATION,
    HTTP_REQUESTS_IN_PROGRESS,
    INCIDENTS_CREATED_TOTAL,
    ALERTS_RECEIVED_TOTAL,
    ML_INFERENCE_TOTAL,
    INTEGRATION_REQUESTS_TOTAL,
    render_metrics,
    get_content_type,
    set_app_info,
    record_http_request,
    record_incident_created,
    record_alert_received,
    record_ml_inference,
    record_integration_request,
)
from .tracing import (
    configure_tracing,
    instrument_fastapi,
    instrument_httpx,
    instrument_redis,
    instrument_celery,
    get_current_trace_context,
    create_span,
)

# Backwards compatibility aliases
REQUEST_COUNT = HTTP_REQUESTS_TOTAL
REQUEST_LATENCY = HTTP_REQUEST_DURATION

__all__ = [
    # Logging
    "configure_logging",
    # Tracing
    "configure_tracing",
    "instrument_fastapi",
    "instrument_httpx",
    "instrument_redis",
    "instrument_celery",
    "get_current_trace_context",
    "create_span",
    # Metrics
    "HTTP_REQUESTS_TOTAL",
    "HTTP_REQUEST_DURATION",
    "HTTP_REQUESTS_IN_PROGRESS",
    "INCIDENTS_CREATED_TOTAL",
    "ALERTS_RECEIVED_TOTAL",
    "ML_INFERENCE_TOTAL",
    "INTEGRATION_REQUESTS_TOTAL",
    "render_metrics",
    "get_content_type",
    "set_app_info",
    "record_http_request",
    "record_incident_created",
    "record_alert_received",
    "record_ml_inference",
    "record_integration_request",
    # Backwards compatibility
    "REQUEST_COUNT",
    "REQUEST_LATENCY",
]
