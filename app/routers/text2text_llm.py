import json
from typing import List

from fastapi import APIRouter, status, Depends, HTTPException
from fastapi.responses import StreamingResponse

from app.database.main_models import User
from app.database.repositories.chat_repository import ChatRepository
from app.dependencies import get_chat_repository, get_llm_repository, get_text_billing_service
from app.dependencies import AUTH_DEPENDENCY
from app.services.t2t_service import UniversalLLM
from app.schemas import ModelT2T, ChatHistoryRequest, ChatMessageResponse, ChatSessionResponse
from app.services.text_billing_service import TextGenBillingService

router = APIRouter(prefix="/chat", tags=["Chat"])



@router.post("/history", response_model=List[ChatMessageResponse])
async def get_chat_history(
        payload: ChatHistoryRequest,
        chat_repo: ChatRepository = Depends(get_chat_repository)
):
    """
    Получает полную историю сообщений для указанного session_id.
    """
    messages = await chat_repo.get_messages_by_session_id(
        session_id=payload.session_id
    )
    return messages or []



@router.post("/completions", status_code=status.HTTP_200_OK)
async def get_text2text(
        payload: ModelT2T,
        user: User = AUTH_DEPENDENCY,
        repo: UniversalLLM = Depends(get_llm_repository),
        billing_service: TextGenBillingService = Depends(get_text_billing_service)
):
    new_balance = await billing_service.process_payment(user, payload.model)

    image_urls_str = [str(url) for url in payload.image_urls] if payload.image_urls else None

    result_text, session_id = await repo.get_response(
        user_id=user.id,
        prompt=payload.prompt,
        model_slug=payload.model,
        session_id=payload.session_id,
        image_urls=image_urls_str
    )

    return {
        "result": result_text,
        "session_id": session_id,
        'user_balance': new_balance,
    }


@router.post("/stream")
async def stream_text2text(
        payload: ModelT2T,
        user: User = AUTH_DEPENDENCY,
        repo: UniversalLLM = Depends(get_llm_repository),
        billing_service: TextGenBillingService = Depends(get_text_billing_service)
):
    new_balance = await billing_service.process_payment(user, payload.model)

    image_urls_str = [str(url) for url in payload.image_urls] if payload.image_urls else None

    async def stream_with_balance():

        balance_data = {
            "type": "balance_update",
            "balance": new_balance
        }

        yield json.dumps(balance_data) + "\n"

        async for chunk in repo.stream_response(
            user_id=user.id,
            prompt=payload.prompt,
            model_slug=payload.model,
            session_id=payload.session_id,
            image_urls=image_urls_str
        ):
            yield chunk

    return StreamingResponse(
        stream_with_balance(),
        media_type="application/x-ndjson"
    )


@router.get("/sessions", response_model=List[ChatSessionResponse])
async def get_user_sessions(
    user: User = AUTH_DEPENDENCY,
    chat_repo: ChatRepository = Depends(get_chat_repository)
):
    return await chat_repo.get_user_sessions(user.id)



@router.delete("/sessions/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_session(
    session_id: int,
    user: User = AUTH_DEPENDENCY,
    chat_repo: ChatRepository = Depends(get_chat_repository)
):
    success = await chat_repo.delete_session(session_id, user.id)
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
    return None