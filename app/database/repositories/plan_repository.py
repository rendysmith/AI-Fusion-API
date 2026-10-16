"""Subscription plan data access repository."""

from sqlalchemy import select, asc, func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from typing import Optional, Sequence

from app.database.subscription_models import SubscriptionPlan, UserSubscription
from app.schemas import SubscriptionPlanCreate, SubscriptionPlanUpdate


class SubscriptionPlanRepository:
    """Repository for SubscriptionPlan operations."""

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]):
        self.session_factory = session_factory

    async def get_by_id(self, plan_id: int) -> Optional[SubscriptionPlan]:
        """Get a plan by its ID."""
        async with self.session_factory() as session:
            return await session.get(SubscriptionPlan, plan_id)

    async def get_by_slug(self, slug: str) -> Optional[SubscriptionPlan]:
        """Get a plan by its slug."""
        async with self.session_factory() as session:
            stmt = select(SubscriptionPlan).where(SubscriptionPlan.slug == slug)
            result = await session.execute(stmt)
            return result.scalars().first()

    async def get_by_name(self, name: str) -> Optional[SubscriptionPlan]:
        """Get a plan by its name."""
        async with self.session_factory() as session:
            stmt = select(SubscriptionPlan).where(SubscriptionPlan.name == name)
            result = await session.execute(stmt)
            return result.scalars().first()

    async def get_all(self, only_active: bool = False) -> Sequence[SubscriptionPlan]:
        """Get all plans ordered by sort_order."""
        async with self.session_factory() as session:
            stmt = select(SubscriptionPlan).order_by(asc(SubscriptionPlan.sort_order))

            if only_active:
                stmt = stmt.where(SubscriptionPlan.is_active == True)

            result = await session.execute(stmt)
            return result.scalars().all()

    async def create(self, payload: SubscriptionPlanCreate) -> SubscriptionPlan:
        """Create a new subscription plan."""
        async with self.session_factory() as session:
            try:
                db_plan = SubscriptionPlan(**payload.model_dump())
                session.add(db_plan)
                await session.commit()
                await session.refresh(db_plan)
                return db_plan
            except IntegrityError as e:
                await session.rollback()
                if "uq_subscription_plans_slug" in str(e):
                    raise ValueError(f"Plan with slug '{payload.slug}' already exists")
                if "uq_subscription_plans_name" in str(e):
                    raise ValueError(f"Plan with name '{payload.name}' already exists")
                raise e

    async def update(
        self, plan_id: int, payload: SubscriptionPlanUpdate,
    ) -> type[SubscriptionPlan] | None:
        """Update an existing subscription plan."""
        async with self.session_factory() as session:
            plan = await session.get(SubscriptionPlan, plan_id)
            if not plan:
                return None

            update_data = payload.model_dump(exclude_unset=True)
            for key, value in update_data.items():
                setattr(plan, key, value)

            try:
                await session.commit()
                await session.refresh(plan)
                return plan
            except IntegrityError as e:
                await session.rollback()
                if "uq_subscription_plans_slug" in str(e):
                    raise ValueError(f"Plan with slug '{payload.slug}' already exists")
                if "uq_subscription_plans_name" in str(e):
                    raise ValueError(f"Plan with name '{payload.name}' already exists")
                raise e

    async def delete(self, plan_id: int) -> bool:
        """Delete a plan if no users are subscribed to it."""
        async with self.session_factory() as session:
            stmt_check = select(func.count(UserSubscription.id)).where(
                UserSubscription.plan_id == plan_id,
            )
            user_count = await session.scalar(stmt_check)

            if user_count and user_count > 0:
                raise ValueError(
                    f"Cannot delete plan: {user_count} users are currently subscribed",
                )

            plan = await session.get(SubscriptionPlan, plan_id)
            if not plan:
                return False

            await session.delete(plan)
            await session.commit()
            return True
