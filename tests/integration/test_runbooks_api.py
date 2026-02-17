from datetime import datetime
from uuid import uuid4

from fastapi.testclient import TestClient

import src.main as main


class FakeRunbookRepo:
    _store = []

    def __init__(self, _):
        self._store = FakeRunbookRepo._store

    async def create(self, runbook):
        if runbook.id is None:
            runbook.id = uuid4()
        if runbook.created_at is None:
            runbook.created_at = datetime.utcnow()
            runbook.updated_at = runbook.created_at
        self._store.append(runbook)
        return runbook

    async def list(self, limit=100, offset=0):
        return self._store[offset : offset + limit]

    async def get(self, runbook_id):
        for runbook in self._store:
            if runbook.id == runbook_id:
                return runbook
        return None


def test_runbooks_endpoints(monkeypatch):
    async def fake_check_db_health():
        return {"connected": True}

    monkeypatch.setattr(main, "init_engine", lambda: None)
    monkeypatch.setattr(main, "close_engine", lambda: None)
    monkeypatch.setattr(main, "check_db_health", fake_check_db_health)
    monkeypatch.setattr("src.routers.runbooks.RunbookRepository", FakeRunbookRepo)

    client = TestClient(main.app)
    payload = {
        "name": "Restart service",
        "description": "Restart app",
        "steps": [{"id": "s1", "type": "notification", "params": {"message": "ok"}}],
        "created_by": "system",
        "tags": [],
        "auto_execute": False,
        "max_concurrent_executions": 1,
    }
    response = client.post("/runbooks/", json=payload)
    assert response.status_code == 200

    response = client.get("/runbooks/")
    assert response.status_code == 200
    assert len(response.json()) == 1
