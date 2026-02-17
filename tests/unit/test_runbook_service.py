import pytest

from src.services.runbook_service import RunbookService


class DummySession:
    def add(self, _):
        return None

    async def flush(self):
        return None


@pytest.mark.asyncio
async def test_runbook_validation_rejects_empty_steps():
    service = RunbookService(session=DummySession())
    with pytest.raises(ValueError):
        service.validate_runbook([])


@pytest.mark.asyncio
async def test_runbook_execution_succeeds():
    service = RunbookService(session=DummySession())
    steps = [
        {"id": "step-1", "type": "wait", "params": {"duration_seconds": 0}},
        {"id": "step-2", "type": "notification", "params": {"message": "ok"}},
    ]
    execution = await service.execute_runbook(
        runbook_id="rb-1",
        runbook_version="1.0.0",
        steps=steps,
        incident_id=None,
        execution_context={},
    )
    assert execution.total_steps == 2
    assert execution.failed_steps == 0
