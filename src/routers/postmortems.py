from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from src.services.postmortem_service import PostmortemService
from src.utils.database import get_db_session

router = APIRouter(prefix="/postmortems", tags=["Postmortems"])


@router.get("/incidents/{incident_id}")
async def generate_postmortem(
    incident_id: UUID,
    session: AsyncSession = Depends(get_db_session),
):
    service = PostmortemService(session)
    try:
        content = await service.generate(incident_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"incident_id": str(incident_id), "postmortem": content}
