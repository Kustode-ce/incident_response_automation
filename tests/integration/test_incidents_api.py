from datetime import datetime
from uuid import uuid4

from fastapi.testclient import TestClient

import src.main as main


class FakeIncidentRepo:
    _store = []

    def __init__(self, _):
        self._store = FakeIncidentRepo._store

    async def create(self, incident):
        if incident.id is None:
            incident.id = uuid4()
        if incident.created_at is None:
            incident.created_at = datetime.utcnow()
            incident.updated_at = incident.created_at
        self._store.append(incident)
        return incident

    async def list(self, limit=100, offset=0):
        return self._store[offset : offset + limit]

    async def get(self, incident_id):
        for incident in self._store:
            if incident.id == incident_id:
                return incident
        return None


def test_incidents_endpoints(monkeypatch):
    async def fake_check_db_health():
        return {"connected": True}

    monkeypatch.setattr(main, "init_engine", lambda: None)
    monkeypatch.setattr(main, "close_engine", lambda: None)
    monkeypatch.setattr(main, "check_db_health", fake_check_db_health)
    monkeypatch.setattr("src.routers.incidents.IncidentRepository", FakeIncidentRepo)

    client = TestClient(main.app)
    payload = {
        "fingerprint": "fp-1",
        "title": "Incident",
        "description": "Test",
        "category": "application",
        "severity": "low",
        "status": "new",
        "labels": {},
        "metadata": {},
        "created_by": "system",
    }
    response = client.post("/incidents/", json=payload)
    assert response.status_code == 200

    response = client.get("/incidents/")
    assert response.status_code == 200
    assert len(response.json()) == 1
