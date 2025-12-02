from fastapi import APIRouter, status

from app.services.t2t_service import UniversalLLM
from app.schemas.ai_model import ModelT2T

router = APIRouter(prefix="/ai-models", tags=["AI Models"])

@router.post("/get_text_to_text", status_code=status.HTTP_200_OK)
async def get_text2text(
        payload: ModelT2T
):
    llm = UniversalLLM()
    result = await llm.get_response(
        prompt=payload.prompt,
        provider=payload.provider,
    )
    return {"result": result}