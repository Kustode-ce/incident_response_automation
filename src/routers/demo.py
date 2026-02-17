from __future__ import annotations

import os
import random
import time
from typing import Optional

from fastapi import APIRouter, HTTPException, Query

from src.observability.metrics import (
    record_sre_burn_rate,
    record_sre_canary_health,
    record_sre_degraded_mode,
    record_sre_disk_pressure,
    record_sre_mitigation,
    record_sre_recovery_ready,
    record_sre_recovery_test,
)

router = APIRouter(prefix="/demo", tags=["Demo"])


def _guard_demo() -> None:
    enabled = os.getenv("DEMO_MODE", "false").lower() in {"1", "true", "yes"}
    if not enabled:
        raise HTTPException(status_code=403, detail="Demo mode disabled")


@router.post("/trigger/slo")
def trigger_slo_breach(
    service: str = "incident-api",
    slo: str = "availability",
    window: str = "5m",
    burn_rate: float = 2.5,
    degraded: bool = True,
):
    _guard_demo()
    record_sre_burn_rate(service=service, slo=slo, window=window, value=burn_rate)
    record_sre_degraded_mode(service=service, reason="slo_breach", degraded=degraded)
    record_sre_mitigation(service=service, action="scale_up", recommended=True)
    return {"status": "ok", "service": service, "slo": slo, "burn_rate": burn_rate}


@router.post("/trigger/canary")
def trigger_canary_signal(
    service: str = "incident-api",
    healthy: bool = False,
    traffic_share: float = 0.1,
):
    _guard_demo()
    record_sre_canary_health(service=service, healthy=healthy, traffic_share=traffic_share)
    return {"status": "ok", "service": service, "healthy": healthy, "traffic_share": traffic_share}


@router.post("/trigger/recovery")
def trigger_recovery_test(
    service: str = "incident-api",
    ready: bool = True,
    status: str = "success",
):
    _guard_demo()
    record_sre_recovery_ready(service=service, ready=ready)
    record_sre_recovery_test(service=service, status=status)
    return {"status": "ok", "service": service, "ready": ready, "result": status}


@router.post("/trigger/disk")
def trigger_disk_pressure(
    service: str = "incident-api",
    mount: str = "/",
    pressure: bool = True,
):
    _guard_demo()
    record_sre_disk_pressure(service=service, mount=mount, pressure=pressure)
    record_sre_mitigation(service=service, action="add_disk", recommended=pressure)
    return {"status": "ok", "service": service, "mount": mount, "pressure": pressure}


@router.post("/trigger/db")
def trigger_db_issue(
    delay_ms: int = Query(250, ge=50, le=2000),
    degrade: bool = True,
):
    _guard_demo()
    time.sleep(delay_ms / 1000.0)
    record_sre_degraded_mode(service="incident-api", reason="db_latency", degraded=degrade)
    return {"status": "ok", "delay_ms": delay_ms}


@router.post("/trigger/mitigation")
def trigger_mitigation(
    service: str = "incident-api",
    action: str = "scale_up",
    recommended: bool = True,
):
    _guard_demo()
    record_sre_mitigation(service=service, action=action, recommended=recommended)
    return {"status": "ok", "service": service, "action": action, "recommended": recommended}


@router.post("/trigger/error")
def trigger_code_error(
    message: Optional[str] = None,
):
    _guard_demo()
    error_message = message or random.choice(
        ["Simulated failure", "Database pool exhausted", "Unexpected None"]
    )
    raise HTTPException(status_code=500, detail=error_message)
