"""
Incident Response Automation API

Main FastAPI application with unified observability setup.
Mirrors medical_billing observability patterns for consistency.
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from src.settings import settings
from src.observability.logging import configure_logging
from src.observability.unified_observability import (
    setup_observability,
    SREMetricsMiddleware,
    record_incident_created,
    record_alert_received,
    record_ml_inference,
    record_integration_request,
)
from src.routers import (
    alerts_router,
    approvals_router,
    audit_logs_router,
    copilot_router,
    demo_router,
    incidents_router,
    integrations_router,
    mitigation_router,
    postmortems_router,
    runbooks_router,
    webhooks_router,
)
from src.utils.database import check_db_health, close_engine, init_engine, get_engine


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    # Configure logging
    configure_logging(settings.log_level)
    
    # Initialize database
    init_engine()
    
    # Setup unified observability (tracing + metrics) - without middleware (added below)
    engine = get_engine()
    setup_observability(
        app=app,
        engine=engine.sync_engine if hasattr(engine, 'sync_engine') else None,
        service_name="incident-api",
        enable_metrics=True,
        enable_tracing=True,
    )
    
    yield
    
    # Cleanup
    await close_engine()


app = FastAPI(
    title="Incident Response Automation",
    version="1.0.0",
    description="AI-powered incident response automation with distributed tracing and SRE metrics",
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# SRE Golden Signals metrics middleware (must be added before app starts)
app.add_middleware(SREMetricsMiddleware, service_name="incident-api")

# Include routers
app.include_router(incidents_router)
app.include_router(alerts_router)
app.include_router(runbooks_router)
app.include_router(integrations_router)
app.include_router(webhooks_router)
app.include_router(copilot_router)
app.include_router(demo_router)
app.include_router(approvals_router)
app.include_router(audit_logs_router)
app.include_router(mitigation_router)
app.include_router(postmortems_router)


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    try:
        db_health = await check_db_health()
        return {
            "status": "ok",
            "service": "incident-api",
            "database": db_health,
        }
    except Exception as exc:
        return JSONResponse(
            status_code=503,
            content={"status": "degraded", "error": str(exc)}
        )


@app.get("/ready")
async def readiness_check():
    """Readiness check for Kubernetes."""
    try:
        db_health = await check_db_health()
        if db_health.get("connected"):
            return {"status": "ready"}
        return JSONResponse(status_code=503, content={"status": "not ready"})
    except Exception:
        return JSONResponse(status_code=503, content={"status": "not ready"})


@app.get("/live")
async def liveness_check():
    """Liveness check for Kubernetes."""
    return {"status": "alive"}


@app.get("/metrics", include_in_schema=False)
async def metrics_endpoint():
    """Prometheus metrics endpoint."""
    from src.observability.metrics import render_metrics, get_content_type
    payload = render_metrics()
    if payload is None:
        return Response(content="Prometheus client not installed", status_code=503)
    return Response(content=payload, media_type=get_content_type())


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "src.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.environment == "development",
    )
