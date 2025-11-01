from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
import uuid

from app.database.repositories.qr_session_repository import QrSessionRepository
from app.services.firebase_service import create_custom_token
from app.database.repositories.user_repository import UserRepository
from app.dependencies import get_user_repository, get_qr_session_repository, check_bot_secret_key
from app.settings import settings
from firebase_admin import auth

router = APIRouter(prefix="/auth", tags=["Authentication"])


temp_qr_sessions = {}


class QrSession(BaseModel):
    session_id: str


@router.post("/qr/session", response_model=QrSession)
async def create_qr_session(
    qr_repo: QrSessionRepository = Depends(get_qr_session_repository)
):

    session_id = str(uuid.uuid4())
    await qr_repo.create_session(session_id)
    return QrSession(session_id=session_id)


class QrStatus(BaseModel):
    status: str
    token: str | None


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
        qr_repo: QrSessionRepository = Depends(get_qr_session_repository)
):

    session = await qr_repo.get_session_status(data.session_id)

    if not session or session["status"] != "pending":
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid or expired session")


    user = await user_repo.get_by_telegram_id(data.telegram_id)

    firebase_uid = None

    if user and user.firebase_uid:
        firebase_uid = user.firebase_uid

    else:

        phantom_email = f"{data.telegram_id}@{settings.FIREBASE_PHANTOM_EMAIL_DOMAIN}"

        try:

            fb_user = auth.create_user(
                email=phantom_email,
                email_verified=True
            )
            firebase_uid = fb_user.uid

        except auth.EmailAlreadyExistsError:

            fb_user = auth.get_user_by_email(phantom_email)
            firebase_uid = fb_user.uid


        if user:
            await user_repo.link_firebase_uid(user.id, firebase_uid, phantom_email)
        else:
            await user_repo.create_user_for_telegram(firebase_uid, phantom_email, data.telegram_id)


    custom_token = create_custom_token(firebase_uid)


    await qr_repo.complete_session(data.session_id, custom_token)

    return {"status": "success", "detail": "Account linked."}