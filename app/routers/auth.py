import logging
import uuid
from pydantic import BaseModel
from fastapi import APIRouter, Depends, HTTPException, status
from firebase_admin import auth


from app import schemas
from app.database.repositories.plan_repository import SubscriptionPlanRepository
from app.database.repositories.subscription_repository import SubscriptionRepository
from app.database.repositories.user_repository import UserRepository
from app.dependencies import get_user_repository, get_qr_session_repository, check_bot_secret_key, \
    get_subscription_repository, get_subscription_plan_repository

from app.database.repositories.qr_session_repository import QrSessionRepository
from app.services.firebase_service import create_custom_token
from app.settings import settings

router = APIRouter(prefix="/auth", tags=["Authentication"])



class QrSession(BaseModel):
    session_id: str


class QrStatus(BaseModel):
    status: str
    token: str | None


@router.post("/qr/session", response_model=QrSession)
async def create_qr_session(
        qr_repo: QrSessionRepository = Depends(get_qr_session_repository)
):
    session_id = str(uuid.uuid4())
    await qr_repo.create_session(session_id)
    return QrSession(session_id=session_id)



@router.get("/qr/session/{session_id}", response_model=QrStatus)
async def get_qr_session_status(
        session_id: str,
        qr_repo: QrSessionRepository = Depends(get_qr_session_repository)
):
    session = await qr_repo.get_session_status(session_id)
    if not session:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Session not found")
    if session["status"] == "completed":
        await qr_repo.delete_session(session_id)
        return QrStatus(status="completed", token=session["token"])
    return QrStatus(status="pending", token=None)



class LinkTelegram(BaseModel):
    session_id: str
    telegram_id: int


@router.post("/qr/link", dependencies=[Depends(check_bot_secret_key)])
async def link_telegram_account(
        data: LinkTelegram,
        user_repo: UserRepository = Depends(get_user_repository),
        qr_repo: QrSessionRepository = Depends(get_qr_session_repository),
        plan_repo: SubscriptionPlanRepository = Depends(get_subscription_plan_repository),
        sub_repo: SubscriptionRepository = Depends(get_subscription_repository)
):
    session = await qr_repo.get_session_status(data.session_id)
    if not session or session["status"] != "pending":
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid or expired session")

    user = await user_repo.get_by_telegram_id(data.telegram_id)
    firebase_uid = None

    if user:

        logging.info(f"QR Link: Найден существующий юзер (ID: {user.id}) по TG ID: {data.telegram_id}")
        firebase_uid = user.firebase_uid

    else:

        logging.info(f"QR Link: Новый юзер по TG ID: {data.telegram_id}. Создаем профиль...")

        phantom_email = f"{data.telegram_id}@{settings.FIREBASE_PHANTOM_EMAIL_DOMAIN}"

        try:
            fb_user = auth.create_user(email=phantom_email, email_verified=True)
            firebase_uid = fb_user.uid
        except auth.EmailAlreadyExistsError:
            fb_user = auth.get_user_by_email(phantom_email)
            firebase_uid = fb_user.uid

        try:
            new_user = await user_repo.create_or_update_profile(
                firebase_uid=firebase_uid,
                email=phantom_email,
                payload=schemas.UserProfileUpdateRequest()
            )


            await user_repo.link_telegram_id(new_user.id, data.telegram_id)


            logging.info(f"QR Link: New user (ID: {new_user.id}). Assigning 'free' plan.")
            free_plan = await plan_repo.get_by_slug("free")

            if free_plan:

                await sub_repo.create_default_subscription(new_user, free_plan)
                logging.info(
                    f"QR Link: Успешно создан профиль (ID: {new_user.id}) и выдан 'free' план с {free_plan.credits_granted} кредитами.")
            else:
                logging.warning(f"QR Link: 'free' plan not found. User created without credits.")

        except Exception as e:
            logging.error(f"QR Link: Не удалось создать профиль в Postgres: {e}")
            raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, "DB profile creation failed")

    if not firebase_uid:
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, "Failed to get Firebase UID")

    custom_token = create_custom_token(firebase_uid)
    await qr_repo.complete_session(data.session_id, custom_token)

    return {"status": "success", "detail": "Account linked."}