from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from typing import Optional

from app.database.main_models import User
from app.database.billing_models import UserSubscription, SubscriptionPlan
from app.schemas import UpdateSubscriptionRequest


class SubscriptionRepository:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]):
        self.session_factory = session_factory

    async def get_active_subscription_by_user_id(self, user_id: int) -> Optional[UserSubscription]:

        async with self.session_factory() as session:
            stmt = (
                select(UserSubscription)
                .where(
                    UserSubscription.user_id == user_id,
                    UserSubscription.status == 'active'
                )
            )
            result = await session.execute(stmt)
            return result.scalars().first()

    async def upsert_subscription(
            self,
            user: User,
            plan: SubscriptionPlan,
            payload: UpdateSubscriptionRequest
    ) -> UserSubscription:

        async with self.session_factory() as session:

            stmt_find = select(UserSubscription).where(UserSubscription.user_id == user.id)
            existing_sub = (await session.execute(stmt_find)).scalars().first()

            if existing_sub:

                existing_sub.plan_id = payload.plan_id
                existing_sub.status = payload.status
                existing_sub.current_period_start = payload.period_start
                existing_sub.current_period_end = payload.period_end
                existing_sub.is_manual = payload.is_manual

                await session.commit()
                await session.refresh(existing_sub)
                return existing_sub
            else:

                new_sub = UserSubscription(
                    id=f"sub_{user.firebase_uid}_{int(datetime.now().timestamp())}",
                    user_id=user.id,
                    plan_id=payload.plan_id,
                    status=payload.status,
                    current_period_start=payload.period_start,
                    current_period_end=payload.period_end,
                    is_manual=payload.is_manual
                )
                session.add(new_sub)
                await session.commit()
                await session.refresh(new_sub)
                return new_sub