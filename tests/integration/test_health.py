from fastapi.testclient import TestClient

import src.main as main


def test_health_endpoint(monkeypatch):
    async def fake_check_db_health():
        return {"connected": True}

    monkeypatch.setattr(main, "init_engine", lambda: None)
    monkeypatch.setattr(main, "close_engine", lambda: None)
    monkeypatch.setattr(main, "check_db_health", fake_check_db_health)

    client = TestClient(main.app)
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
