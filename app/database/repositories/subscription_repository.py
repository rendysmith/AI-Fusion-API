"""Subscription data access repository."""

import logging
from datetime import datetime, timezone, timedelta

from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from typing import Optional

from sqlalchemy.orm import joinedload

from app.database.main_models import User
from app.database.repositories.plan_repository import SubscriptionPlanRepository
from app.database.subscription_models import UserSubscription, SubscriptionPlan
from app.schemas import UpdateSubscriptionRequest


class SubscriptionRepository:
    """Repository for UserSubscription operations."""

    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        plan_repo: SubscriptionPlanRepository,
    ):
        self.session_factory = session_factory
        self.plan_repo = plan_repo

    async def get_active_subscription_by_user_id(
        self, user_id: int,
    ) -> Optional[UserSubscription]:
        """Get the active subscription for a user."""
        async with self.session_factory() as session:
            stmt = (
                select(UserSubscription)
                .where(
                    UserSubscription.user_id == user_id,
                    UserSubscription.status.in_(["active", "pending_cancellation"]),
                )
            )
            result = await session.execute(stmt)
            return result.scalars().first()

    async def upsert_subscription(
        self,
        user: User,
        plan: SubscriptionPlan,
        payload: UpdateSubscriptionRequest,
    ) -> UserSubscription:
        """Create or update a user's subscription."""
        async with self.session_factory() as session:
            stmt_find = select(UserSubscription).where(
                UserSubscription.user_id == user.id,
            )
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
                    is_manual=payload.is_manual,
                )
                session.add(new_sub)
                await session.commit()
                await session.refresh(new_sub)
                return new_sub

    async def create_default_subscription(self, user: User, free_plan: SubscriptionPlan):
        """Create a default free subscription for a user."""
        async with self.session_factory() as session:
            sub_id = f"sub_{user.firebase_uid}_{int(datetime.now().timestamp())}"

            new_sub = UserSubscription(
                id=sub_id,
                user_id=user.id,
                plan_id=free_plan.id,
                status="active",
                is_manual=True,
                current_period_start=datetime.now(timezone.utc),
                current_period_end=datetime.now(timezone.utc) + timedelta(days=365 * 100),
            )
            session.add(new_sub)

            stmt_balance = (
                update(User)
                .where(User.id == user.id)
                .values(balance=User.balance + free_plan.credits_granted)
            )
            await session.execute(stmt_balance)

            try:
                await session.commit()
            except IntegrityError:
                await session.rollback()

    async def get_active_subscription_with_plan(
        self, user_id: int,
    ) -> Optional[UserSubscription]:
        """Get active subscription with plan details loaded."""
        async with self.session_factory() as session:
            stmt = (
                select(UserSubscription)
                .where(
                    UserSubscription.user_id == user_id,
                    UserSubscription.status.in_(["active", "pending_cancellation"]),
                )
                .options(joinedload(UserSubscription.plan))
            )
            result = await session.execute(stmt)
            return result.scalars().first()

    async def activate_subscription(self, user_id: int, plan_id: int):
        """Activate a new subscription plan for a user."""
        async with self.session_factory() as session:
            plan = await session.get(SubscriptionPlan, plan_id)
            if not plan:
                raise ValueError(f"Plan {plan_id} not found")

            await session.execute(
                update(UserSubscription)
                .where(
                    UserSubscription.user_id == user_id,
                    UserSubscription.status == "active",
                )
                .values(status="cancelled"),
            )

            new_sub = UserSubscription(
                id=f"sub_{user_id}_{int(datetime.now().timestamp())}",
                user_id=user_id,
                plan_id=plan_id,
                status="active",
                is_manual=False,
                current_period_start=datetime.now(timezone.utc),
                current_period_end=datetime.now(timezone.utc) + timedelta(days=30),
            )
            session.add(new_sub)

            if plan.credits_granted > 0:
                await session.execute(
                    update(User)
                    .where(User.id == user_id)
                    .values(balance=User.balance + plan.credits_granted),
                )

            await session.commit()

    async def cancel_subscription(self, user_id: int) -> Optional[UserSubscription]:
        """Cancel a user's subscription and revert to free plan if needed."""
        async with self.session_factory() as session:
            active_sub = await self.get_active_subscription_with_plan(user_id)

            if not active_sub or active_sub.plan.slug == "free":
                return None

            now = datetime.now(timezone.utc)

            if active_sub.current_period_end and active_sub.current_period_end > now:
                active_sub.status = "pending_cancellation"
                await session.commit()
                await session.refresh(active_sub)
                return active_sub
            else:
                active_sub.status = "cancelled"

                free_plan = await self.plan_repo.get_by_slug("free")
                new_free_sub = UserSubscription(
                    id=f"sub_{user_id}_{int(datetime.now().timestamp())}",
                    user_id=user_id,
                    plan_id=free_plan.id,
                    status="active",
                    is_manual=True,
                    current_period_start=now,
                    current_period_end=now + timedelta(days=365 * 100),
                )
                session.add(new_free_sub)
                await session.commit()
                return new_free_sub

    async def check_and_downgrade_expired_subs(self):
        """Find expired subscriptions and downgrade them to Free plan."""
        async with self.session_factory() as session:
            now = datetime.now(timezone.utc)

            stmt = select(UserSubscription).where(
                UserSubscription.status.in_(["active", "pending_cancellation"]),
                UserSubscription.current_period_end < now,
            )
            expired_subs = (await session.execute(stmt)).scalars().all()

            free_plan = await self.plan_repo.get_by_slug("free")
            if not free_plan:
                return

            for sub in expired_subs:
                sub.status = "expired"

                new_free_sub = UserSubscription(
                    id=f"sub_{sub.user_id}_{int(datetime.now().timestamp())}",
                    user_id=sub.user_id,
                    plan_id=free_plan.id,
                    status="active",
                    is_manual=True,
                    current_period_start=now,
                    current_period_end=now + timedelta(days=365 * 100),
                )
                session.add(new_free_sub)

            await session.commit()
