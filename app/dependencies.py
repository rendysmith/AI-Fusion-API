import logging

import aiohttp
from fastapi import Depends, HTTPException, Security
from fastapi.security import OAuth2PasswordBearer, APIKeyHeader
from starlette import status
from fastapi import Request

from app.database.main_models import User
from app.database.redis_db import get_redis_client
from app.database.repositories.ai_model_repository import AiModelRepository
from app.database.repositories.analytics_repository import AnalyticsRepository
from app.database.repositories.billing_repository import BillingRepository
from app.database.repositories.circuit_breaker_repository import CircuitBreakerRepository
from app.database.engine import async_session_factory
from app.database.repositories.plan_access_repository import PlanAccessRepository
from app.database.repositories.plan_repository import SubscriptionPlanRepository
from app.database.repositories.product_repository import ProductRepository
from app.database.repositories.qr_session_repository import QrSessionRepository
from app.database.repositories.subscription_repository import SubscriptionRepository
from app.database.repositories.task_repository import TaskRepository
from app.database.repositories.telegram_token_repository import TelegramTokenRepository
from app.database.repositories.template_repository import TemplateRepository

from app.database.repositories.user_repository import UserRepository
from app.services.billing_service import BillingService
from app.services.firebase_service import verify_firebase_token

import redis.asyncio as aioredis

from app.services.getcourse_service import GetCourseService
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


def get_http_session(request: Request) -> aiohttp.ClientSession:
    """Достает "вечный" ClientSession из app.state."""
    return request.app.state.http_session

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


def get_subscription_plan_repository() -> SubscriptionPlanRepository:
    return SubscriptionPlanRepository(async_session_factory)


def get_plan_access_repository() -> PlanAccessRepository:
    return PlanAccessRepository(async_session_factory)


def get_subscription_repository(
    plan_repo: SubscriptionPlanRepository = Depends(get_subscription_plan_repository)
) -> SubscriptionRepository:

    return SubscriptionRepository(
        session_factory=async_session_factory,
        plan_repo=plan_repo
    )


def get_billing_repository() -> BillingRepository:
    return BillingRepository(async_session_factory)

def get_billing_service(
    user_repo: UserRepository = Depends(get_user_repository),
    sub_repo: SubscriptionRepository = Depends(get_subscription_repository)
) -> BillingService:

    return BillingService(user_repo=user_repo, sub_repo=sub_repo)


def get_getcourse_service(session: aiohttp.ClientSession = Depends(get_http_session)) -> GetCourseService:

    if not settings.GETCOURSE_API_KEY or not settings.GETCOURSE_ACCOUNT_NAME:
        logging.warning("GetCourse .env vars not set. Checkout will fail.")
        pass

    return GetCourseService(
        api_key=settings.GETCOURSE_API_KEY,
        account_name=settings.GETCOURSE_ACCOUNT_NAME,
        admin_email=settings.GETCOURSE_ADMIN_EMAIL,
        client=session
    )


def get_product_repository() -> ProductRepository:
    return ProductRepository(async_session_factory)