from fastapi import APIRouter, Depends, status

from app.services.t2t_service import UniversalLLM
from app.dependencies import get_ai_model_repository
from app.schemas.ai_model import ModelT2T



router = APIRouter(prefix="/ai-models", tags=["AI Models"])

@router.post("/get_text_to_text", status_code=status.HTTP_200_OK)
async def get_text2text(
        payload: ModelT2T,
        repo: UniversalLLM = Depends(get_ai_model_repository)
):

    result = await repo.get_response(
        prompt=payload.prompt,
        provider=payload.provider,
    )
    return {"result": result}