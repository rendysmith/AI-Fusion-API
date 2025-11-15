import asyncio
import logging
from datetime import datetime, timezone, timedelta

import aiohttp
import redis.asyncio as aioredis
from fastapi import Depends, HTTPException, Security, Request, status
from fastapi.security import OAuth2PasswordBearer, APIKeyHeader
from sqlalchemy.exc import IntegrityError
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app import schemas
from app.database.main_models import User
from app.database.engine import async_session_factory
from app.database.subscription_models import UserSubscription
from app.services.firebase_service import verify_firebase_token
from app.settings import settings

#
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


async def get_current_user(
        token: str = Depends(oauth2_scheme),
        user_repo: UserRepository = Depends(get_user_repository),
        plan_repo: SubscriptionPlanRepository = Depends(get_subscription_plan_repository),
        sub_repo: SubscriptionRepository = Depends(get_subscription_repository)
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
        if firebase_uid is None:
            raise credentials_exception


        user = await user_repo.get_by_firebase_uid(uid=firebase_uid)


        if user:
            return user



        logging.info(f"New user detected (UID: {firebase_uid}). Lazy creating profile...")

        try:

            async with user_repo.session_factory() as session:
                async with session.begin():


                    user_payload = schemas.UserProfileUpdateRequest()


                    stmt_insert_user = pg_insert(User).values(
                        firebase_uid=firebase_uid,
                        email=email,
                        **user_payload.model_dump(exclude_unset=True)
                    ).on_conflict_do_nothing().returning(User)

                    user = (await session.execute(stmt_insert_user)).scalar_one_or_none()

                    if user is None:

                        logging.warning(f"Race condition detected for {firebase_uid}. Refetching...")
                        user = await user_repo.get_by_firebase_uid(uid=firebase_uid)
                        if user: return user
                        raise Exception("Failed to create or find user after race.")


                    free_plan = await plan_repo.get_by_slug("free")

                    if free_plan:

                        sub_id = f"sub_{user.firebase_uid}_{int(datetime.now().timestamp())}"
                        new_sub = UserSubscription(
                            id=sub_id,
                            user_id=user.id,
                            plan_id=free_plan.id,
                            status='active',
                            is_manual=True,
                            current_period_end=datetime.now(timezone.utc) + timedelta(days=365 * 100)
                        )
                        session.add(new_sub)


                        if free_plan.credits_granted > 0:
                            user.balance = user.balance + free_plan.credits_granted
                            session.add(user)

                        logging.info(f"Assigned 'free' plan with {free_plan.credits_granted} credits.")

                await session.refresh(user, attribute_names=['subscription'])
                if user.subscription:
                    await session.refresh(user.subscription, attribute_names=['plan'])

            logging.info(f"Lazy registration complete for {firebase_uid}.")
            return user

        except IntegrityError as e:
            logging.warning(f"Race condition (IntegrityError) during lazy registration for {firebase_uid}: {e}")

            user = await user_repo.get_by_firebase_uid(uid=firebase_uid)
            if user: return user
            raise credentials_exception

        except Exception as e:
            logging.error(f"Critical error during lazy registration: {e}", exc_info=True)
            raise credentials_exception

    except ValueError:
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