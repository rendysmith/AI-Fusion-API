from decimal import Decimal
from typing import Optional, Any, Sequence

from sqlalchemy import update, func
from sqlalchemy.ext.asyncio import async_sessionmaker
from sqlalchemy.future import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import selectinload

from app import schemas
from app.database.subscription_models import UserSubscription, SubscriptionPlan
from app.database.main_models import User


class BaseRepository:
    def __init__(self, session_factory: async_sessionmaker):
        self.session_factory = session_factory


class UserRepository(BaseRepository):

    async def get_by_id(self, user_id: int) -> User | None:
        async with self.session_factory() as session:
            return await session.get(User, user_id)

    async def get_by_firebase_uid(self, uid: str) -> User | None:
        async with self.session_factory() as session:

            stmt = (
                select(User)
                .where(User.firebase_uid == uid)
                .options(
                    selectinload(User.subscription)
                    .joinedload(UserSubscription.plan)
                )
            )
            result = await session.execute(stmt)
            return result.scalars().first()

    async def get_by_telegram_id(self, telegram_id: int) -> User | None:
        async with self.session_factory() as session:
            stmt = select(User).where(User.telegram_id == telegram_id)
            result = await session.execute(stmt)
            return result.scalars().first()

    async def link_telegram_id(self, user_id: int, telegram_id: int) -> User:

        async with self.session_factory() as session:
            stmt = update(User).where(User.id == user_id) \
                .values(telegram_id=telegram_id) \
                .returning(User)

            result = await session.execute(stmt)
            await session.commit()
            return result.scalars().one()

    async def link_firebase_uid(self, user_id: int, uid: str, email: str):

        async with self.session_factory() as session:
            stmt = update(User).where(User.id == user_id) \
                .values(firebase_uid=uid, email=email)
            await session.execute(stmt)
            await session.commit()

    async def deduct_balance(self, user_id: int, amount: float) -> Optional[Decimal]:
        async with self.session_factory() as session:
            stmt = (
                update(User)
                .where(
                    User.id == user_id,
                    User.balance >= amount
                )
                .values(balance=User.balance - amount)
                .returning(User.balance)
            )

            new_balance = await session.scalar(stmt)

            await session.commit()

            return new_balance

    async def refund_balance(self, user_id: int, amount: float):

        async with self.session_factory() as session:
            stmt = (
                update(User)
                .where(User.id == user_id)
                .values(balance=User.balance + amount)
            )
            await session.execute(stmt)
            await session.commit()


    async def get_by_username(self, username: str) -> User | None:
        async with self.session_factory() as session:
            stmt = select(User).where(User.username == username)
            result = await session.execute(stmt)
            return result.scalars().first()

    async def create_or_update_profile(
            self,
            firebase_uid: str,
            email: Optional[str],
            payload: schemas.UserProfileUpdateRequest
    ) -> User:

        async with self.session_factory() as session:

            update_data = payload.model_dump(exclude_unset=True)


            stmt = pg_insert(User).values(
                firebase_uid=firebase_uid,
                email=email,
                **update_data
            )

            if not update_data:
                on_conflict_stmt = stmt.on_conflict_do_nothing(
                    index_elements=['firebase_uid']
                )
            else:

                on_conflict_stmt = stmt.on_conflict_do_update(
                    index_elements=['firebase_uid'],
                    set_=update_data
                )

            await session.execute(on_conflict_stmt)
            await session.commit()


            user = await self.get_by_firebase_uid(firebase_uid)
            if user is None:
                raise Exception("User not found after UPSERT. This should not happen.")

            return user

    async def get_all_paginated_with_subs(
            self, page: int, limit: int
    ) -> tuple[Sequence[User], int | None | Any]:

        offset = (page - 1) * limit

        async with self.session_factory() as session:

            stmt_users = (
                select(User)
                .order_by(User.created_at.desc())
                .offset(offset)
                .limit(limit)
                .options(

                    selectinload(User.subscription).joinedload(UserSubscription.plan)
                )
            )
            result_users = await session.execute(stmt_users)
            users = result_users.scalars().unique().all()


            stmt_count = select(func.count(User.id))
            total = (await session.scalar(stmt_count)) or 0

            return users, total


    async def block_user(self, firebase_uid: str, is_blocked: bool) -> Optional[User]:
        async with self.session_factory() as session:
            user = await self.get_by_firebase_uid(firebase_uid)
            if not user:
                return None

            user.is_blocked = is_blocked
            await session.commit()
            await session.refresh(user)
            return user

    async def get_user_active_plan(self, user_id: int) -> Optional[SubscriptionPlan]:

        async with self.session_factory() as session:
            stmt = (
                select(SubscriptionPlan)
                .join(UserSubscription, UserSubscription.plan_id == SubscriptionPlan.id)
                .where(
                    UserSubscription.user_id == user_id,
                    UserSubscription.status == 'active'
                )
            )
            result = await session.execute(stmt)
            return result.scalars().first()

    async def add_credits(self, user_id: int, amount: int):

        async with self.session_factory() as session:
            stmt = (
                update(User)
                .where(User.id == user_id)
                .values(balance=User.balance + amount)
            )
            await session.execute(stmt)
            await session.commit()