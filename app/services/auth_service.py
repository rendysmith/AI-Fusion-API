import logging
from datetime import datetime, timezone, timedelta
from sqlalchemy import select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from app.database.main_models import User
from app.database.subscription_models import SubscriptionPlan, UserSubscription

logger = logging.getLogger(__name__)


class AuthService:
    def __init__(self, user_repo, plan_repo):
        self.user_repo = user_repo
        self.plan_repo = plan_repo

    async def get_or_create_user(self, firebase_uid: str, email: str, is_trusted: bool) -> User:
        user = await self.user_repo.get_by_firebase_uid(firebase_uid)

        if not user:
            await self._create_user_entry(firebase_uid, email)
            user = await self.user_repo.get_by_firebase_uid(firebase_uid)

        if user and is_trusted and user.subscription is None:
            await self._grant_free_plan(user)
            user = await self.user_repo.get_by_firebase_uid(firebase_uid)

        return user

    async def _create_user_entry(self, firebase_uid: str, email: str):

        async with self.user_repo.session_factory() as session:
            async with session.begin():
                stmt = pg_insert(User).values(
                    firebase_uid=firebase_uid,
                    email=email
                ).on_conflict_do_nothing()
                await session.execute(stmt)

    async def _grant_free_plan(self, user: User):
        logger.info(f"Granting FREE plan to trusted user {user.id}...")
        async with self.user_repo.session_factory() as session:
            async with session.begin():
                stmt_find_plan = select(SubscriptionPlan).where(SubscriptionPlan.slug == "free")
                free_plan = (await session.execute(stmt_find_plan)).scalar_one_or_none()

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
                        await session.execute(
                            update(User)
                            .where(User.id == user.id)
                            .values(balance=free_plan.credits_granted)
                        )