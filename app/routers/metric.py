from fastapi import APIRouter, Depends, Request, status

from app.schemas.metric import VisitorTrackRequest
from app.database.repositories.metric_repository import VisitorRepository
from app.dependencies import get_visitor_repository

router = APIRouter(prefix="/metrics", tags=["Metrics"])

@router.post("/track-visit", status_code=status.HTTP_200_OK)
async def track_visit(
        payload: VisitorTrackRequest,
        request: Request,
        visitor_repo: VisitorRepository = Depends(get_visitor_repository)
):
    # Получаем User-Agent
    user_agent = request.headers.get("user-agent")

    await visitor_repo.track_visit(
        visitor_id=payload.visitor_id,
        referrer=payload.referrer,
        user_agent=user_agent
    )
    return {"status": "tracked"}