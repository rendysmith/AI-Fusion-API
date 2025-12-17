import asyncio
import logging
from datetime import datetime, timezone, timedelta
from typing import Any, AsyncGenerator

import aiohttp
import redis.asyncio as aioredis
from fastapi import Depends, HTTPException, Security, Request, status
from fastapi.security import OAuth2PasswordBearer, APIKeyHeader
from sqlalchemy import update, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app import schemas
from app.database.main_models import User
from app.database.engine import async_session_factory
from app.database.repositories.priority_model_repository import PriorityModelRepository
from app.database.repositories.system_repository import SystemRepository
from app.database.subscription_models import UserSubscription, SubscriptionPlan
from app.services.auth_service import AuthService
from app.services.firebase_service import verify_firebase_token
from app.services.s3_uploader import S3UploaderService
from app.services.t2i_service import UniversalImageGenerator
from app.services.t2t_service import UniversalLLM
from app.settings import settings

from app.database.repositories.user_repository import UserRepository
from app.database.repositories.task_repository import TaskRepository
from app.database.repositories.analytics_repository import AnalyticsRepository
from app.database.repositories.subscription_repository import SubscriptionRepository
from app.database.repositories.plan_repository import SubscriptionPlanRepository
from app.database.repositories.ai_model_repository import AiModelRepository
from app.database.repositories.template_repository import TemplateRepository
from app.database.repositories.plan_access_repository import PlanAccessRepository
from app.database.repositories.billing_repository import BillingRepository
from app.database.repositories.product_repository import ProductRepository
from app.database.repositories.telegram_token_repository import TelegramTokenRepository
from app.database.repositories.qr_session_repository import QrSessionRepository
from app.database.repositories.circuit_breaker_repository import CircuitBreakerRepository
from app.database.repositories.metric_repository import VisitorRepository

from app.services.billing_service import BillingService
from app.services.getcourse_service import GetCourseService


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/token")
api_key_header = APIKeyHeader(name="Authorization", auto_error=False)


def get_http_session(request: Request) -> aiohttp.ClientSession:
    """Достает "вечный" ClientSession из app.state."""
    return request.app.state.http_session


def get_redis_client() -> aioredis.Redis:
    """Возвращает 'сырой' redis-клиент (мы его не создавали в 'state')"""

    from app.database.redis_db import redis_pool
    return aioredis.Redis(connection_pool=redis_pool)


async def check_bot_secret_key(header: str = Security(api_key_header)):
    """Проверяет, что запрос пришел от нашего бота (по Bearer токену)."""
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




def get_user_repository() -> UserRepository:
    return UserRepository(async_session_factory)


def get_task_repository() -> TaskRepository:
    return TaskRepository(async_session_factory)


def get_analytics_repository() -> AnalyticsRepository:
    return AnalyticsRepository(async_session_factory)


async def get_async_session() -> AsyncGenerator[Any, Any]:

    async with async_session_factory() as session:
        yield session

def get_subscription_plan_repository() -> SubscriptionPlanRepository:
    return SubscriptionPlanRepository(async_session_factory)


def get_subscription_repository(
        plan_repo: SubscriptionPlanRepository = Depends(get_subscription_plan_repository)
) -> SubscriptionRepository:
    return SubscriptionRepository(
        session_factory=async_session_factory,
        plan_repo=plan_repo
    )


def get_telegram_token_repository() -> TelegramTokenRepository:
    return TelegramTokenRepository(async_session_factory)

def get_visitor_repository() -> VisitorRepository:
    return VisitorRepository(async_session_factory)

def get_qr_session_repository(
        redis_client: aioredis.Redis = Depends(get_redis_client)
) -> QrSessionRepository:
    return QrSessionRepository(redis_client)


def get_circuit_breaker_repository(
        redis_client: aioredis.Redis = Depends(get_redis_client)
) -> CircuitBreakerRepository:
    return CircuitBreakerRepository(redis_client)


def get_ai_model_repository() -> AiModelRepository:
    return AiModelRepository(async_session_factory)


def get_template_repository() -> TemplateRepository:
    return TemplateRepository(async_session_factory)


def get_plan_access_repository() -> PlanAccessRepository:
    return PlanAccessRepository(async_session_factory)


def get_billing_repository() -> BillingRepository:
    return BillingRepository(async_session_factory)


def get_product_repository() -> ProductRepository:
    return ProductRepository(async_session_factory)


def get_system_repository(
        redis_client: aioredis.Redis = Depends(get_redis_client)
) -> SystemRepository:
    return SystemRepository(redis_client)


def get_billing_service(
        user_repo: UserRepository = Depends(get_user_repository),
        sub_repo: SubscriptionRepository = Depends(get_subscription_repository)
) -> BillingService:
    return BillingService(user_repo=user_repo, sub_repo=sub_repo)


def get_getcourse_service(
        request: Request,
        billing_repo: BillingRepository = Depends(get_billing_repository),
        billing_service: BillingService = Depends(get_billing_service)
) -> GetCourseService:
    if not settings.GETCOURSE_API_KEY or not settings.GETCOURSE_ACCOUNT_NAME:
        logging.warning("GetCourse .env vars not set. Checkout will fail.")

        return GetCourseService(
            api_key="dummy", account_name="dummy",
            admin_email="dummy", client=request.app.state.http_session,
            billing_repo=billing_repo, billing_service=billing_service
        )

    return GetCourseService(
        api_key=settings.GETCOURSE_API_KEY,
        account_name=settings.GETCOURSE_ACCOUNT_NAME,
        admin_email=settings.GETCOURSE_ADMIN_EMAIL,
        client=request.app.state.http_session,
        billing_repo=billing_repo,
        billing_service=billing_service
    )


def get_auth_service(
    user_repo=Depends(get_user_repository),
    plan_repo=Depends(get_subscription_plan_repository)
) -> AuthService:
    return AuthService(user_repo, plan_repo)


async def get_current_user(
        token: str = Depends(oauth2_scheme),
        auth_service: AuthService = Depends(get_auth_service)
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        decoded_token = await asyncio.to_thread(verify_firebase_token, token)
        firebase_uid = decoded_token.get("uid")
        email = decoded_token.get("email")

        if not firebase_uid:
            raise credentials_exception

        is_email_verified = decoded_token.get("email_verified", False)
        sign_in_provider = decoded_token.get("firebase", {}).get("sign_in_provider")

        is_trusted_provider = (
                is_email_verified or
                sign_in_provider in ['google.com', 'apple.com']
        )

        user = await auth_service.get_or_create_user(
            firebase_uid=firebase_uid,
            email=email,
            is_trusted=is_trusted_provider
        )

        if not user:
            raise credentials_exception

        return user

    except Exception as e:
        logging.error(f"Auth dependency error: {e}")
        raise credentials_exception


async def get_current_admin_user(
        user: User = Depends(get_current_user)
) -> User:
    """
    "Охранник" админки. Проверяет, что у юзера есть флаг 'is_admin'.
    """
    if not user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access forbidden: requires admin privileges."
        )
    return user

def get_visitor_repository() -> VisitorRepository:
    return VisitorRepository(async_session_factory)

def get_chat_repository() -> PriorityModelRepository:
    return PriorityModelRepository(async_session_factory)

def get_llm_repository() -> UniversalLLM:
    return UniversalLLM(async_session_factory)

def get_image_repository() -> UniversalImageGenerator:
    return UniversalImageGenerator(async_session_factory)


def get_s3_uploader(request: Request) -> S3UploaderService:
    return S3UploaderService(request.app.state.s3_client)