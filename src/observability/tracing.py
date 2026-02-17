"""OpenTelemetry Tracing Configuration for Incident Response Automation."""

from __future__ import annotations

import logging
import os
from typing import Optional

logger = logging.getLogger(__name__)

# Optional imports - only if OpenTelemetry is installed
try:
    from opentelemetry import trace
    from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
    from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
    from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
    from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
    from opentelemetry.instrumentation.redis import RedisInstrumentor
    from opentelemetry.instrumentation.celery import CeleryInstrumentor
    from opentelemetry.propagate import set_global_textmap
    from opentelemetry.propagators.b3 import B3MultiFormat
    from opentelemetry.sdk.resources import Resource, SERVICE_NAME, SERVICE_VERSION
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
    from opentelemetry.sdk.trace.sampling import TraceIdRatioBased
    OTEL_AVAILABLE = True
except ImportError:
    OTEL_AVAILABLE = False
    logger.warning("OpenTelemetry not installed. Tracing disabled.")


def configure_tracing(
    service_name: Optional[str] = None,
    service_version: Optional[str] = None,
    otlp_endpoint: Optional[str] = None,
    sample_rate: float = 1.0,
    enable_console_exporter: bool = False,
) -> Optional[trace.Tracer]:
    """
    Configure OpenTelemetry tracing for the application.
    
    Args:
        service_name: Name of the service (default: from env or 'incident-response-api')
        service_version: Version of the service (default: from env or '1.0.0')
        otlp_endpoint: OTLP exporter endpoint (default: from env)
        sample_rate: Trace sampling rate (0.0 to 1.0)
        enable_console_exporter: Also log traces to console (for debugging)
    
    Returns:
        Tracer instance or None if OTEL is not available
    """
    if not OTEL_AVAILABLE:
        logger.warning("OpenTelemetry not available. Skipping tracing configuration.")
        return None

    # Get configuration from environment or parameters
    service_name = service_name or os.getenv("OTEL_SERVICE_NAME", "incident-response-api")
    service_version = service_version or os.getenv("OTEL_SERVICE_VERSION", "1.0.0")
    otlp_endpoint = otlp_endpoint or os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT")
    
    # Create resource with service information
    resource = Resource.create({
        SERVICE_NAME: service_name,
        SERVICE_VERSION: service_version,
        "deployment.environment": os.getenv("ENVIRONMENT", "development"),
    })
    
    # Create tracer provider with sampling
    sampler = TraceIdRatioBased(sample_rate)
    provider = TracerProvider(resource=resource, sampler=sampler)
    
    # Add OTLP exporter if endpoint is configured
    if otlp_endpoint:
        logger.info(f"Configuring OTLP exporter to {otlp_endpoint}")
        otlp_exporter = OTLPSpanExporter(
            endpoint=otlp_endpoint,
            insecure=True,  # Use insecure for local development
        )
        provider.add_span_processor(BatchSpanProcessor(otlp_exporter))
    else:
        logger.warning("OTEL_EXPORTER_OTLP_ENDPOINT not set. Traces will not be exported.")
    
    # Add console exporter for debugging
    if enable_console_exporter:
        provider.add_span_processor(BatchSpanProcessor(ConsoleSpanExporter()))
    
    # Set the global tracer provider
    trace.set_tracer_provider(provider)
    
    # Set up B3 propagation (compatible with Jaeger, Zipkin)
    set_global_textmap(B3MultiFormat())
    
    logger.info(f"OpenTelemetry tracing configured for {service_name} v{service_version}")
    
    return trace.get_tracer(service_name, service_version)


def instrument_fastapi(app) -> None:
    """Instrument FastAPI application with OpenTelemetry."""
    if not OTEL_AVAILABLE:
        return
    
    FastAPIInstrumentor.instrument_app(
        app,
        excluded_urls="/health,/metrics,/docs,/openapi.json",
    )
    logger.info("FastAPI instrumented with OpenTelemetry")


def instrument_httpx() -> None:
    """Instrument HTTPX client with OpenTelemetry."""
    if not OTEL_AVAILABLE:
        return
    
    HTTPXClientInstrumentor().instrument()
    logger.info("HTTPX instrumented with OpenTelemetry")


def instrument_sqlalchemy(engine) -> None:
    """Instrument SQLAlchemy engine with OpenTelemetry."""
    if not OTEL_AVAILABLE:
        return
    
    SQLAlchemyInstrumentor().instrument(engine=engine)
    logger.info("SQLAlchemy instrumented with OpenTelemetry")


def instrument_redis() -> None:
    """Instrument Redis client with OpenTelemetry."""
    if not OTEL_AVAILABLE:
        return
    
    RedisInstrumentor().instrument()
    logger.info("Redis instrumented with OpenTelemetry")


def instrument_celery() -> None:
    """Instrument Celery with OpenTelemetry."""
    if not OTEL_AVAILABLE:
        return
    
    CeleryInstrumentor().instrument()
    logger.info("Celery instrumented with OpenTelemetry")


def get_current_trace_context() -> dict:
    """Get the current trace context for logging and correlation."""
    if not OTEL_AVAILABLE:
        return {}
    
    span = trace.get_current_span()
    if span and span.is_recording():
        ctx = span.get_span_context()
        return {
            "trace_id": format(ctx.trace_id, "032x"),
            "span_id": format(ctx.span_id, "016x"),
        }
    return {}


def create_span(name: str, attributes: Optional[dict] = None):
    """
    Create a new span for tracing.
    
    Usage:
        with create_span("process_incident", {"incident_id": "123"}) as span:
            # Your code here
            span.set_attribute("result", "success")
    """
    if not OTEL_AVAILABLE:
        from contextlib import nullcontext
        return nullcontext()
    
    tracer = trace.get_tracer(__name__)
    span = tracer.start_as_current_span(name, attributes=attributes)
    return span
