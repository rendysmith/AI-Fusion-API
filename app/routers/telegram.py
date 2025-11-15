import uuid
import qrcode
import io
import base64
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, HTTPException, status

from app import schemas
from app.database.main_models import User
from app.dependencies import get_current_user, check_bot_secret_key
from app.database.repositories.user_repository import UserRepository

from app.database.repositories.telegram_token_repository import TelegramTokenRepository
from app.dependencies import get_user_repository, get_telegram_token_repository


TELEGRAM_BOT_NAME = "Viralexai_bot"

router = APIRouter(prefix="/auth/telegram", tags=["Telegram Auth"])


@router.post("/init", response_model=schemas.TelegramInitResponse)
async def init_telegram_linking(
        user: User = Depends(get_current_user),
        token_repo: TelegramTokenRepository = Depends(get_telegram_token_repository)
):

    token = f"tg_auth_{uuid.uuid4().hex}"
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=5)


    await token_repo.create_token(
        token=token,
        firebase_uid=user.firebase_uid,
        expires_at=expires_at
    )

    bot_url = f"https://t.me/{TELEGRAM_BOT_NAME}?start={token}"


    img = qrcode.make(bot_url)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    qr_base64 = base64.b64encode(buf.getvalue()).decode('utf-8')
    qr_data_uri = f"data:image/png;base64,{qr_base64}"

    return schemas.TelegramInitResponse(
        token=token,
        expires_at=expires_at,
        bot_url=bot_url,
        qr_code=qr_data_uri
    )


@router.get("/status/{token}", response_model=schemas.TelegramStatusResponse)
async def get_telegram_linking_status(
        token: str,
        token_repo: TelegramTokenRepository = Depends(get_telegram_token_repository)
):

    token_data = await token_repo.get_token(token)

    if not token_data:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Token not found or invalid")

    if token_data.status == 'pending' and token_data.expires_at < datetime.now(timezone.utc):
        return schemas.TelegramStatusResponse(status="expired")

    return schemas.TelegramStatusResponse(
        status=token_data.status,
        expires_at=token_data.expires_at,
        telegram_id=token_data.telegram_id,
        telegram_username=token_data.telegram_username,
        linked_at=token_data.updated_at if token_data.status == 'completed' else None
    )


@router.post("/webhook", dependencies=[Depends(check_bot_secret_key)])
async def telegram_bot_webhook(
        payload: schemas.TelegramWebhookPayload,
        user_repo: UserRepository = Depends(get_user_repository),
        token_repo: TelegramTokenRepository = Depends(get_telegram_token_repository)
):


    token_data = await token_repo.get_token(payload.token)
    if not token_data or token_data.status != 'pending' or token_data.expires_at < datetime.now(timezone.utc):

        return {"ok": False, "error": "Token invalid or expired"}


    user = await user_repo.get_by_firebase_uid(token_data.firebase_uid)
    if not user:
        return {"ok": False, "error": "User profile not found"}


    await user_repo.link_telegram_id(user.id, payload.telegram_id)


    await token_repo.complete_token(
        token=payload.token,
        telegram_id=payload.telegram_id,
        telegram_username=payload.username
    )

    return {"ok": True, "message": "Account linked successfully"}