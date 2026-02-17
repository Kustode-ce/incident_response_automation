from datetime import datetime
from uuid import uuid4

from fastapi.testclient import TestClient

import src.main as main


class FakeAlertRepo:
    _store = []

    def __init__(self, _):
        self._store = FakeAlertRepo._store

    async def create(self, alert):
        if alert.id is None:
            alert.id = uuid4()
        if alert.created_at is None:
            alert.created_at = datetime.utcnow()
        self._store.append(alert)
        return alert

    async def list(self, limit=100, offset=0):
        return self._store[offset : offset + limit]


def test_alerts_endpoints(monkeypatch):
    async def fake_check_db_health():
        return {"connected": True}

    monkeypatch.setattr(main, "init_engine", lambda: None)
    monkeypatch.setattr(main, "close_engine", lambda: None)
    monkeypatch.setattr(main, "check_db_health", fake_check_db_health)
    monkeypatch.setattr("src.routers.alerts.AlertRepository", FakeAlertRepo)

    client = TestClient(main.app)
    payload = {
        "source": "prometheus",
        "status": "firing",
        "severity": "high",
        "message": "CPU high",
        "fingerprint": "fp-1",
        "labels": {},
        "annotations": {},
    }
    response = client.post("/alerts/", json=payload)
    assert response.status_code == 200

    response = client.get("/alerts/")
    assert response.status_code == 200
    assert len(response.json()) == 1
