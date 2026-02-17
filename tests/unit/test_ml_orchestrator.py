import pytest

from src.models.enums import MLTaskType
from src.services.ml.orchestrator import MLOrchestrator


@pytest.mark.asyncio
async def test_ml_orchestrator_sets_task():
    orchestrator = MLOrchestrator()
    response = await orchestrator.run(
        task=MLTaskType.classification,
        payload={"summary": "cpu spike"},
        incident_id=None,
    )
    assert response.task == MLTaskType.classification
