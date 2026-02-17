import asyncio
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from src.models import Incident
from src.repositories.base import BaseRepository


@pytest.mark.asyncio
async def test_base_repository_get_executes_query():
    session = AsyncMock()
    result = MagicMock()
    result.scalar_one_or_none.return_value = None
    session.execute.return_value = result

    repo = BaseRepository(session, Incident)
    await repo.get(uuid4())

    session.execute.assert_called_once()


@pytest.mark.asyncio
async def test_base_repository_create_adds_entity():
    session = AsyncMock()
    entity = Incident(
        fingerprint="abc",
        title="title",
        description="desc",
        category="application",
        severity="low",
        status="new",
    )

    repo = BaseRepository(session, Incident)
    await repo.create(entity)

    session.add.assert_called_once_with(entity)
