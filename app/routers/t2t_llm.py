from typing import List

from fastapi import APIRouter, status

from app.database.ai_model import ChatMessage
from app.database.engine import async_session_factory
from app.database.main_models import User
from app.database.repositories.priority_model_repository import PriorityModelRepository
from app.main import AUTH_DEPENDENCY
from app.services.t2t_service import UniversalLLM
from app.schemas import ModelT2T

router = APIRouter(prefix="/ai-models", tags=["AI Models"])


class ChatHistoryRequest:
    pass


@router.post("/get_history", response_model=List[ChatMessage])  # Предполагаем, что ChatMessage - это схема ответа
async def get_chat_history(
        payload: ChatHistoryRequest,
        chat_repo: ChatRepository = Depends(get_chat_repository)
):
    """
    Получает полную историю сообщений для указанного session_id,
    отсортированную в хронологическом порядке.
    """
    chat_repo = PriorityModelRepository(async_session_factory)
    messages = await chat_repo.get_messages_by_session_id(
        session_id=payload.session_id
    )

    if not messages:
        return []

    return messages

@router.post("/get_text_to_text", status_code=status.HTTP_200_OK)
async def get_text2text(
        payload: ModelT2T
):
    llm = UniversalLLM()
    result = await llm.get_response(
        model=payload.model,
        prompt=payload.prompt)

    return {"result": result}