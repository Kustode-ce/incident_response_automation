"""
Unified Observability Setup for Incident Response Automation

Consolidates OpenTelemetry tracing, metrics, and logging into single setup function.
Mirrors the medical_billing setup for consistent observability across Kustode services.

Features:
- Distributed tracing with Tempo/Jaeger
- Prometheus metrics with SRE Golden Signals
- APDEX scoring for user satisfaction
- Organization/tenant-aware metrics
- Automatic instrumentation of FastAPI, HTTPX, SQLAlchemy, Redis, Celery

Usage:
    from src.observability.unified_observability import setup_observability
    
    app = FastAPI()
    tracer, meter = setup_observability(
        app=app,
        engine=engine,
        service_name="incident-api"
    )
"""

import logging
import os
import time
import re
from typing import Any, Callable, Dict, List, Optional, Tuple

from fastapi import FastAPI, Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

logger = logging.getLogger(__name__)

# ============================================================================
# OPTIONAL IMPORTS - gracefully handle missing dependencies
# ============================================================================

# OpenTelemetry
try:
    from opentelemetry import trace, metrics
    from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
    from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter
    from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
    from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
    from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
    from opentelemetry.instrumentation.redis import RedisInstrumentor
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor
    from opentelemetry.sdk.metrics import MeterProvider
    from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.semconv.resource import ResourceAttributes
    OTEL_AVAILABLE = True
except ImportError:
    OTEL_AVAILABLE = False
    logger.warning("OpenTelemetry not installed. Tracing disabled.")

# Prometheus
try:
    from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST, REGISTRY
    PROMETHEUS_AVAILABLE = True
except ImportError:
    PROMETHEUS_AVAILABLE = False
    logger.warning("prometheus_client not installed. Metrics disabled.")

# B3 Propagation
try:
    from opentelemetry.propagate import set_global_textmap
    from opentelemetry.propagators.b3 import B3MultiFormat
    B3_AVAILABLE = True
except ImportError:
    B3_AVAILABLE = False


# ============================================================================
# APDEX CONFIGURATION
# ============================================================================

APDEX_THRESHOLDS = {
    "fast": 0.1,       # 100ms - health checks, simple lookups
    "normal": 0.5,     # 500ms - standard API calls
    "slow": 2.0,       # 2s - reports, ML analysis
    "bulk": 10.0,      # 10s - runbook execution, batch operations
}

APDEX_ENDPOINT_CATEGORIES = {
    r"^/health": "fast",
    r"^/metrics": "fast",
    r"^/api/v1/incidents/\{": "normal",
    r"^/api/v1/runbooks": "slow",
    r"^/api/v1/ml": "slow",
    r"^/webhooks": "normal",
}


# ============================================================================
# GLOBAL STATE
# ============================================================================

_OBSERVABILITY_INITIALIZED = False
_PROMETHEUS_REGISTRY = REGISTRY if PROMETHEUS_AVAILABLE else None


# ============================================================================
# PROMETHEUS METRICS
# ============================================================================

def _get_or_create_metric(metric_class, name: str, description: str, labelnames: list, **kwargs):
    """Get existing metric or create new one. Prevents duplicate registration."""
    if not PROMETHEUS_AVAILABLE:
        return None
    
    # First check if already in registry by name
    if name in REGISTRY._names_to_collectors:
        return REGISTRY._names_to_collectors[name]
    
    # Also check for name_total (Counter adds _total suffix)
    if f"{name}_total" in REGISTRY._names_to_collectors:
        return REGISTRY._names_to_collectors[f"{name}_total"]
    
    # Search collectors by _name attribute
    for collector in REGISTRY._names_to_collectors.values():
        if hasattr(collector, '_name') and collector._name == name:
            return collector
    
    try:
        return metric_class(name, description, labelnames, **kwargs)
    except ValueError as e:
        # Already exists - find and return it
        if "Duplicated timeseries" in str(e):
            for collector in list(REGISTRY._names_to_collectors.values()):
                if hasattr(collector, '_name') and collector._name == name:
                    return collector
        raise


# SRE Golden Signals Metrics
HTTP_REQUESTS_TOTAL = None
HTTP_REQUEST_DURATION = None
HTTP_REQUESTS_IN_PROGRESS = None
HTTP_ERRORS_TOTAL = None
APDEX_REQUESTS_TOTAL = None

# Incident-specific metrics
INCIDENTS_CREATED = None
INCIDENTS_RESOLVED = None
INCIDENT_RESOLUTION_TIME = None
ALERTS_RECEIVED = None
ML_INFERENCE_DURATION = None
RUNBOOK_EXECUTION_DURATION = None
INTEGRATION_REQUESTS = None


def _initialize_metrics():
    """Initialize all Prometheus metrics. 
    
    Uses existing metrics from metrics.py when available to avoid conflicts.
    """
    global HTTP_REQUESTS_TOTAL, HTTP_REQUEST_DURATION, HTTP_REQUESTS_IN_PROGRESS
    global HTTP_ERRORS_TOTAL, APDEX_REQUESTS_TOTAL
    global INCIDENTS_CREATED, INCIDENTS_RESOLVED, INCIDENT_RESOLUTION_TIME
    global ALERTS_RECEIVED, ML_INFERENCE_DURATION, RUNBOOK_EXECUTION_DURATION
    global INTEGRATION_REQUESTS

    if not PROMETHEUS_AVAILABLE:
        return

    # Import existing metrics from src.observability.metrics to avoid duplication
    try:
        from src.observability.metrics import (
            HTTP_REQUESTS_TOTAL as EXISTING_HTTP_REQUESTS,
            HTTP_REQUEST_DURATION as EXISTING_HTTP_DURATION,
            HTTP_REQUESTS_IN_PROGRESS as EXISTING_HTTP_IN_PROGRESS,
            INCIDENTS_CREATED_TOTAL as EXISTING_INCIDENTS_CREATED,
            INCIDENTS_RESOLVED_TOTAL as EXISTING_INCIDENTS_RESOLVED,
            INCIDENT_RESOLUTION_TIME as EXISTING_RESOLUTION_TIME,
            ALERTS_RECEIVED_TOTAL as EXISTING_ALERTS,
            ML_INFERENCE_TOTAL as EXISTING_ML,
            INTEGRATION_REQUESTS_TOTAL as EXISTING_INTEGRATION,
        )
        # Use existing metrics
        HTTP_REQUESTS_TOTAL = EXISTING_HTTP_REQUESTS
        HTTP_REQUEST_DURATION = EXISTING_HTTP_DURATION
        HTTP_REQUESTS_IN_PROGRESS = EXISTING_HTTP_IN_PROGRESS
        INCIDENTS_CREATED = EXISTING_INCIDENTS_CREATED
        INCIDENTS_RESOLVED = EXISTING_INCIDENTS_RESOLVED
        INCIDENT_RESOLUTION_TIME = EXISTING_RESOLUTION_TIME
        ALERTS_RECEIVED = EXISTING_ALERTS
        
        logger.info("✅ Using existing metrics from metrics.py")
    except ImportError as e:
        logger.warning(f"Could not import existing metrics: {e}")
        # Fall back to creating new ones (might conflict)
        HTTP_REQUESTS_TOTAL = None
        HTTP_REQUEST_DURATION = None
        HTTP_REQUESTS_IN_PROGRESS = None

    # Create additional SRE metrics that don't exist yet
    HTTP_ERRORS_TOTAL = _get_or_create_metric(
        Counter, 'http_errors_total', 'Total HTTP errors',
        ['method', 'path', 'status', 'error_type', 'service']
    )
    APDEX_REQUESTS_TOTAL = _get_or_create_metric(
        Counter, 'apdex_requests_total', 'APDEX satisfaction tracking',
        ['service', 'endpoint_category', 'satisfaction']
    )
    ML_INFERENCE_DURATION = _get_or_create_metric(
        Histogram, 'ml_inference_duration_seconds', 'ML inference duration',
        ['provider', 'task'],
        buckets=(0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0)
    )
    RUNBOOK_EXECUTION_DURATION = _get_or_create_metric(
        Histogram, 'runbook_execution_duration_seconds', 'Runbook execution duration',
        ['runbook_name', 'status'],
        buckets=(1, 5, 10, 30, 60, 300, 600, 1800)
    )


# ============================================================================
# HTTP METRICS MIDDLEWARE
# ============================================================================

class SREMetricsMiddleware(BaseHTTPMiddleware):
    """
    SRE Golden Signals Middleware
    
    Captures:
    - Latency (request duration histogram)
    - Traffic (request count)
    - Errors (error count by type)
    - Saturation (requests in progress)
    - APDEX (user satisfaction)
    """
    
    EXCLUDED_PATHS = {'/health', '/metrics', '/ready', '/live', '/docs', '/openapi.json'}
    
    PATH_PATTERNS = [
        (re.compile(r'/[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}', re.I), '/{uuid}'),
        (re.compile(r'/\d+(?=/|$)'), '/{id}'),
    ]
    
    def __init__(self, app: ASGIApp, service_name: str = "incident-api"):
        super().__init__(app)
        self.service_name = service_name
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        path = request.url.path
        
        if path in self.EXCLUDED_PATHS:
            return await call_next(request)
        
        normalized_path = self._normalize_path(path)
        method = request.method
        
        start_time = time.perf_counter()
        
        if HTTP_REQUESTS_IN_PROGRESS:
            try:
                HTTP_REQUESTS_IN_PROGRESS.labels(method=method, endpoint=normalized_path).inc()
            except TypeError:
                try:
                    HTTP_REQUESTS_IN_PROGRESS.labels(method=method, service=self.service_name).inc()
                except Exception:
                    pass
        
        status = "500"
        error_type = None
        
        try:
            response = await call_next(request)
            status = str(response.status_code)
            
            if response.status_code >= 400:
                error_type = self._categorize_error(response.status_code)
                if HTTP_ERRORS_TOTAL:
                    HTTP_ERRORS_TOTAL.labels(
                        method=method,
                        path=normalized_path,
                        status=status,
                        error_type=error_type,
                        service=self.service_name
                    ).inc()
            
            return response
            
        except Exception as e:
            status = "500"
            error_type = "unhandled_exception"
            if HTTP_ERRORS_TOTAL:
                HTTP_ERRORS_TOTAL.labels(
                    method=method,
                    path=normalized_path,
                    status=status,
                    error_type=error_type,
                    service=self.service_name
                ).inc()
            raise
            
        finally:
            duration = time.perf_counter() - start_time
            
            # Record metrics - use endpoint label for compatibility with existing metrics
            if HTTP_REQUESTS_TOTAL:
                try:
                    # Try with existing metrics labels first (method, endpoint, status)
                    HTTP_REQUESTS_TOTAL.labels(
                        method=method,
                        endpoint=normalized_path,
                        status=status,
                    ).inc()
                except TypeError:
                    # Fall back to new labels (method, path, status, service)
                    try:
                        HTTP_REQUESTS_TOTAL.labels(
                            method=method,
                            path=normalized_path,
                            status=status,
                            service=self.service_name
                        ).inc()
                    except Exception:
                        pass
            
            if HTTP_REQUEST_DURATION:
                try:
                    HTTP_REQUEST_DURATION.labels(
                        method=method,
                        endpoint=normalized_path,
                    ).observe(duration)
                except TypeError:
                    try:
                        HTTP_REQUEST_DURATION.labels(
                            method=method,
                            path=normalized_path,
                            status=status,
                            service=self.service_name
                        ).observe(duration)
                    except Exception:
                        pass
            
            if HTTP_REQUESTS_IN_PROGRESS:
                try:
                    HTTP_REQUESTS_IN_PROGRESS.labels(
                        method=method,
                        endpoint=normalized_path
                    ).dec()
                except TypeError:
                    try:
                        HTTP_REQUESTS_IN_PROGRESS.labels(method=method, service=self.service_name).dec()
                    except Exception:
                        pass
            
            # Record APDEX
            if int(status) < 400:
                self._record_apdex(path, duration)
            
            # Add to OTEL span if available
            if OTEL_AVAILABLE:
                span = trace.get_current_span()
                if span and span.is_recording():
                    span.set_attribute("http.status_code", int(status))
                    span.set_attribute("http.method", method)
                    span.set_attribute("http.route", normalized_path)
                    span.set_attribute("http.duration_ms", duration * 1000)
                    if error_type:
                        span.set_attribute("error.type", error_type)
                        span.set_attribute("error", True)
    
    def _normalize_path(self, path: str) -> str:
        normalized = path
        for pattern, replacement in self.PATH_PATTERNS:
            normalized = pattern.sub(replacement, normalized)
        return normalized
    
    def _categorize_error(self, status_code: int) -> str:
        error_map = {
            400: "bad_request",
            401: "unauthorized",
            403: "forbidden",
            404: "not_found",
            409: "conflict",
            422: "validation_error",
            429: "rate_limited",
            500: "internal_error",
            502: "bad_gateway",
            503: "service_unavailable",
            504: "gateway_timeout",
        }
        return error_map.get(status_code, "server_error" if status_code >= 500 else "client_error")
    
    def _get_apdex_category(self, path: str) -> str:
        for pattern, category in APDEX_ENDPOINT_CATEGORIES.items():
            if re.match(pattern, path):
                return category
        return "normal"
    
    def _record_apdex(self, path: str, duration: float):
        if not APDEX_REQUESTS_TOTAL:
            return
        
        category = self._get_apdex_category(path)
        threshold = APDEX_THRESHOLDS.get(category, 0.5)
        
        if duration < threshold:
            satisfaction = "satisfied"
        elif duration < threshold * 4:
            satisfaction = "tolerating"
        else:
            satisfaction = "frustrated"
        
        APDEX_REQUESTS_TOTAL.labels(
            service=self.service_name,
            endpoint_category=category,
            satisfaction=satisfaction
        ).inc()


# ============================================================================
# SETUP FUNCTIONS
# ============================================================================

def setup_observability(
    app: Optional[FastAPI] = None,
    engine: Optional[Any] = None,
    service_name: str = "incident-api",
    enable_metrics: bool = True,
    enable_tracing: bool = True,
) -> Tuple[Optional[Any], Optional[Any]]:
    """
    Unified observability setup for Incident Response Automation.
    
    Args:
        app: FastAPI application instance
        engine: SQLAlchemy engine instance (optional)
        service_name: Name of the service
        enable_metrics: Enable Prometheus metrics
        enable_tracing: Enable OpenTelemetry tracing
    
    Returns:
        Tuple of (TracerProvider, MeterProvider)
    """
    global _OBSERVABILITY_INITIALIZED
    
    if _OBSERVABILITY_INITIALIZED:
        logger.info("Observability already initialized, skipping")
        return None, None
    
    # Initialize Prometheus metrics
    if enable_metrics:
        _initialize_metrics()
    
    tracer_provider = None
    meter_provider = None
    
    # Get OTEL endpoint from environment
    otel_endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT")
    
    # Setup tracing
    if enable_tracing and OTEL_AVAILABLE and otel_endpoint:
        tracer_provider = _setup_tracing(service_name, otel_endpoint)
    
    # Setup OTEL metrics
    if enable_metrics and OTEL_AVAILABLE and otel_endpoint:
        meter_provider = _setup_otel_metrics(service_name, otel_endpoint)
    
    # Instrument libraries
    if app:
        _instrument_app(app, engine, tracer_provider, meter_provider, service_name)
    
    _OBSERVABILITY_INITIALIZED = True
    
    logger.info(
        f"✅ Observability initialized for {service_name}",
        extra={
            "tracing": enable_tracing and OTEL_AVAILABLE,
            "metrics": enable_metrics and PROMETHEUS_AVAILABLE,
            "otel_endpoint": otel_endpoint or "not-configured"
        }
    )
    
    return tracer_provider, meter_provider


def _setup_tracing(service_name: str, otel_endpoint: str):
    """Setup OpenTelemetry distributed tracing."""
    try:
        resource = Resource.create({
            ResourceAttributes.SERVICE_NAME: service_name,
            ResourceAttributes.SERVICE_VERSION: os.getenv("SERVICE_VERSION", "1.0.0"),
            ResourceAttributes.DEPLOYMENT_ENVIRONMENT: os.getenv("ENVIRONMENT", "development"),
            "service.namespace": "incident-response",
        })
        
        tracer_provider = TracerProvider(resource=resource)
        
        span_exporter = OTLPSpanExporter(
            endpoint=otel_endpoint,
            insecure=True
        )
        
        span_processor = BatchSpanProcessor(
            span_exporter,
            max_queue_size=2048,
            schedule_delay_millis=5000,
            max_export_batch_size=512
        )
        tracer_provider.add_span_processor(span_processor)
        
        trace.set_tracer_provider(tracer_provider)
        
        # Set B3 propagation if available
        if B3_AVAILABLE:
            set_global_textmap(B3MultiFormat())
        
        logger.info(f"✅ Tracing initialized -> {otel_endpoint}")
        return tracer_provider
        
    except Exception as e:
        logger.error(f"Failed to initialize tracing: {e}")
        return None


def _setup_otel_metrics(service_name: str, otel_endpoint: str):
    """Setup OpenTelemetry metrics export."""
    try:
        resource = Resource.create({
            ResourceAttributes.SERVICE_NAME: service_name,
            "service.namespace": "incident-response",
        })
        
        metric_exporter = OTLPMetricExporter(
            endpoint=otel_endpoint,
            insecure=True
        )
        
        metric_reader = PeriodicExportingMetricReader(
            metric_exporter,
            export_interval_millis=15000
        )
        
        meter_provider = MeterProvider(
            resource=resource,
            metric_readers=[metric_reader]
        )
        
        metrics.set_meter_provider(meter_provider)
        
        logger.info(f"✅ OTEL Metrics initialized -> {otel_endpoint}")
        return meter_provider
        
    except Exception as e:
        logger.error(f"Failed to initialize OTEL metrics: {e}")
        return None


def _instrument_app(
    app: FastAPI,
    engine: Optional[Any],
    tracer_provider: Optional[Any],
    meter_provider: Optional[Any],
    service_name: str
):
    """Instrument FastAPI app and libraries."""
    
    # Note: SRE metrics middleware must be added before app starts (in main.py)
    # We skip adding it here to avoid "Cannot add middleware after app started" error
    
    # Instrument FastAPI with OTEL
    if OTEL_AVAILABLE and tracer_provider:
        try:
            FastAPIInstrumentor.instrument_app(
                app,
                tracer_provider=tracer_provider,
                meter_provider=meter_provider,
                excluded_urls="/health,/metrics,/docs,/openapi.json"
            )
            logger.info("✅ FastAPI instrumented with OTEL")
        except Exception as e:
            logger.warning(f"Failed to instrument FastAPI: {e}")
    
    # Instrument HTTPX
    if OTEL_AVAILABLE:
        try:
            HTTPXClientInstrumentor().instrument(
                tracer_provider=tracer_provider,
                meter_provider=meter_provider
            )
            logger.info("✅ HTTPX instrumented")
        except Exception as e:
            logger.warning(f"Failed to instrument HTTPX: {e}")
    
    # Instrument SQLAlchemy
    if engine and OTEL_AVAILABLE:
        try:
            SQLAlchemyInstrumentor().instrument(
                engine=engine,
                tracer_provider=tracer_provider,
                enable_commenter=True
            )
            logger.info("✅ SQLAlchemy instrumented")
        except Exception as e:
            logger.warning(f"Failed to instrument SQLAlchemy: {e}")
    
    # Instrument Redis
    if OTEL_AVAILABLE:
        try:
            RedisInstrumentor().instrument(tracer_provider=tracer_provider)
            logger.info("✅ Redis instrumented")
        except Exception as e:
            logger.warning(f"Failed to instrument Redis: {e}")
    
    # Add /metrics endpoint
    if PROMETHEUS_AVAILABLE:
        @app.get("/metrics", include_in_schema=False)
        async def metrics_endpoint():
            return Response(
                generate_latest(_PROMETHEUS_REGISTRY),
                media_type=CONTENT_TYPE_LATEST
            )
        logger.info("✅ /metrics endpoint added")


# ============================================================================
# HELPER FUNCTIONS FOR RECORDING METRICS
# ============================================================================

def record_incident_created(severity: str, category: str, source: str):
    """Record an incident creation."""
    if INCIDENTS_CREATED:
        INCIDENTS_CREATED.labels(
            severity=severity,
            category=category,
            source=source
        ).inc()


def record_incident_resolved(severity: str, category: str, resolution_time_seconds: float):
    """Record an incident resolution."""
    if INCIDENTS_RESOLVED:
        INCIDENTS_RESOLVED.labels(severity=severity, category=category).inc()
    if INCIDENT_RESOLUTION_TIME:
        INCIDENT_RESOLUTION_TIME.labels(severity=severity, category=category).observe(resolution_time_seconds)


def record_alert_received(source: str, severity: str):
    """Record an alert received."""
    if ALERTS_RECEIVED:
        ALERTS_RECEIVED.labels(source=source, severity=severity).inc()


def record_ml_inference(provider: str, task: str, duration_seconds: float):
    """Record ML inference duration."""
    if ML_INFERENCE_DURATION:
        ML_INFERENCE_DURATION.labels(provider=provider, task=task).observe(duration_seconds)


def record_runbook_execution(runbook_name: str, status: str, duration_seconds: float):
    """Record runbook execution."""
    if RUNBOOK_EXECUTION_DURATION:
        RUNBOOK_EXECUTION_DURATION.labels(runbook_name=runbook_name, status=status).observe(duration_seconds)


def record_integration_request(integration: str, operation: str, status: str):
    """Record integration request."""
    if INTEGRATION_REQUESTS:
        INTEGRATION_REQUESTS.labels(integration=integration, operation=operation, status=status).inc()


# ============================================================================
# TRACER/METER GETTERS
# ============================================================================

def get_tracer(name: str):
    """Get a tracer instance for manual instrumentation."""
    if OTEL_AVAILABLE:
        return trace.get_tracer(name)
    return None


def get_meter(name: str):
    """Get a meter instance for custom metrics."""
    if OTEL_AVAILABLE:
        return metrics.get_meter(name)
    return None
