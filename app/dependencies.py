from fastapi import Depends, HTTPException, Security
from fastapi.security import OAuth2PasswordBearer, APIKeyHeader
from starlette import status

from app.database.main_models import User
from app.database.redis_db import get_redis_client
from app.database.repositories.ai_model_repository import AiModelRepository
from app.database.repositories.analytics_repository import AnalyticsRepository
from app.database.repositories.circuit_breaker_repository import CircuitBreakerRepository
from app.database.engine import async_session_factory
from app.database.repositories.qr_session_repository import QrSessionRepository
from app.database.repositories.task_repository import TaskRepository
from app.database.repositories.telegram_token_repository import TelegramTokenRepository
from app.database.repositories.template_repository import TemplateRepository

from app.database.repositories.user_repository import UserRepository
from app.services.firebase_service import verify_firebase_token

import redis.asyncio as aioredis

from app.settings import settings


def get_user_repository() -> UserRepository:
    return UserRepository(async_session_factory)


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/token")


async def get_current_user(
        token: str = Depends(oauth2_scheme),
        user_repo: UserRepository = Depends(get_user_repository)
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    profile_not_found_exception = HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="User profile not found. Please complete registration.",
        headers={"X-Error-Code": "PROFILE_NOT_FOUND"},
    )

    try:
        decoded_token = verify_firebase_token(token)
        firebase_uid = decoded_token.get("uid")

        if firebase_uid is None:
            raise credentials_exception

        user = await user_repo.get_by_firebase_uid(uid=firebase_uid)

        if user is None:
            raise profile_not_found_exception

        return user

    except ValueError:
        raise credentials_exception


def get_task_repository() -> TaskRepository:
    return TaskRepository(async_session_factory)

def get_analytics_repository() -> AnalyticsRepository:
    return AnalyticsRepository(async_session_factory)


def get_telegram_token_repository() -> TelegramTokenRepository:
    return TelegramTokenRepository(async_session_factory)


def get_qr_session_repository(
    redis_client: aioredis.Redis = Depends(get_redis_client)
) -> QrSessionRepository:
    return QrSessionRepository(redis_client)


def get_circuit_breaker_repository(
    redis_client: aioredis.Redis = Depends(get_redis_client)
) -> CircuitBreakerRepository:
    return CircuitBreakerRepository(redis_client)


api_key_header = APIKeyHeader(name="Authorization", auto_error=False)


async def check_bot_secret_key(header: str = Security(api_key_header)):

    if not header:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing Authorization Header"
        )

    if header == f"Bearer {settings.BOT_SECRET_KEY}":
        return True

    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Invalid or missing bot secret key"
    )


def get_ai_model_repository() -> AiModelRepository:
    return AiModelRepository(async_session_factory)



async def get_current_admin_user(
    user: User = Depends(get_current_user)
) -> User:

    if not user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access forbidden: requires admin privileges."
        )
    return user


def get_template_repository() -> TemplateRepository:
    return TemplateRepository(async_session_factory)