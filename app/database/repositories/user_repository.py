import logging
from decimal import Decimal
from typing import Optional, Any, Sequence

from sqlalchemy import update, func, or_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import async_sessionmaker
from sqlalchemy.future import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import selectinload

from app import schemas
from app.database.billing_models import PaymentInvoice
from app.database.metric_models import Visitor
from app.database.subscription_models import UserSubscription, SubscriptionPlan
from app.database.main_models import User
from app.database.task_models import GenerationTask

from app.services.referral_service import HasherRef


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
                    selectinload(User.subscription).joinedload(UserSubscription.plan)
                )
            )
            result = await session.execute(stmt)
            return result.scalars().first()

    async def get_by_telegram_id(self, telegram_id: int) -> User | None:
        async with self.session_factory() as session:
            stmt = (
                select(User)
                .where(User.telegram_id == telegram_id)
                .options(
                    selectinload(User.subscription).joinedload(UserSubscription.plan)
                )
            )
            result = await session.execute(stmt)
            return result.scalars().first()

    async def link_telegram_id(self, user_id: int,
                               telegram_id: int) -> User | None:

        async with self.session_factory() as session:
            try:
                stmt = update(User).where(User.id == user_id) \
                    .values(telegram_id=telegram_id) \
                    .returning(User)

                result = await session.execute(stmt)
                await session.commit()
                return result.scalars().one()

            except IntegrityError as e:

                await session.rollback()
                logging.warning(f"Failed to link TG ID {telegram_id} to User {user_id}: {e}")
                return None

    async def link_firebase_uid(self, user_id: int, uid: str, email: str):

        async with self.session_factory() as session:
            stmt = update(User).where(User.id == user_id) \
                .values(firebase_uid=uid, email=email)
            await session.execute(stmt)
            await session.commit()

    async def deduct_balance(self, user_id: int, amount: float) -> Optional[Decimal]:

        amount_decimal = Decimal(str(amount))

        async with self.session_factory() as session:
            stmt = (
                update(User)
                .where(
                    User.id == user_id,
                    User.balance >= amount_decimal
                )
                .values(balance=User.balance - amount_decimal)
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

    async def add_credits_smart(self, identifier: str, amount: int) -> bool:
        """
        Ищет юзера по Telegram ID или Email и начисляет кредиты.
        """
        async with self.session_factory() as session:
            stmt = select(User)


            if identifier.isdigit():

                tg_id = int(identifier)
                stmt = stmt.where(User.telegram_id == tg_id)
            else:

                stmt = stmt.where(User.email == identifier)

            user = (await session.execute(stmt)).scalars().first()

            if not user:
                return False

            user.balance += Decimal(amount)

            await session.commit()
            return True

    async def get_user_full_details(self, identifier: str) -> dict:

        async with self.session_factory() as session:


            stmt_user = select(User).options(
                selectinload(User.subscription).joinedload(UserSubscription.plan)
            )


            if identifier.isdigit():

                stmt_user = stmt_user.where(User.id == int(identifier))
            else:

                stmt_user = stmt_user.where(User.firebase_uid == identifier)

            user = (await session.execute(stmt_user)).scalars().first()

            if not user:
                return None

            real_user_id = user.id


            stmt_visitor = select(Visitor).where(Visitor.user_id == real_user_id)
            visitor = (await session.execute(stmt_visitor)).scalars().first()


            stmt_tasks = select(
                func.count(GenerationTask.id).label("total"),
                func.count(GenerationTask.id).filter(GenerationTask.status == 'completed').label("success"),
                func.sum(GenerationTask.cost).label("spent")
            ).where(GenerationTask.user_id == real_user_id)

            task_stats = (await session.execute(stmt_tasks)).one()


            stmt_money = select(func.sum(PaymentInvoice.amount)).where(
                PaymentInvoice.user_id == real_user_id,
                PaymentInvoice.status == 'paid'
            )
            money_spent = (await session.scalar(stmt_money)) or 0

            return {
                "user": user,
                "visitor": visitor,
                "stats": {
                    "total_generations": task_stats.total or 0,
                    "successful_generations": task_stats.success or 0,
                    "total_credits_spent": task_stats.spent or 0.0,
                    "total_money_paid": money_spent
                }
            }

    async def register_user(self, payload: schemas.UserRegisterRequest) -> User:
        """
        Создает нового пользователя с проверкой реферального кода.
        Если пользователь уже есть - возвращает ошибку (или существующего).
        """
        async with self.session_factory() as session:

            stmt = select(User).where(
                or_(
                    User.firebase_uid == payload.firebase_uid,
                    User.email == payload.email
                )
            )
            existing_user = (await session.execute(stmt)).scalars().first()

            if existing_user:

                raise ValueError("User already exists")



            new_user = User(
                firebase_uid=payload.firebase_uid,
                email=payload.email,
                username=payload.username,
                photo_url=payload.photo_url,
                registration_method='email',
                balance=0.0
            )


            if payload.referral_code:

                referrer_id = HasherRef.decode(payload.referral_code)

                if referrer_id:

                    ref_stmt = select(User).where(User.id == referrer_id)
                    referrer = (await session.execute(ref_stmt)).scalars().first()


                    if referrer and not referrer.is_blocked:

                        new_user.referred_by_id = referrer.id

                        referrer.balance = User.balance + 100

                        session.add(referrer)


            session.add(new_user)

            try:
                await session.commit()
                await session.refresh(new_user)
            except IntegrityError:
                await session.rollback()
                raise ValueError("Database error during registration")

            return new_user

    async def get_telegram_ids_paginated(self, limit: int, offset: int) -> list[int]:
        async with self.session_factory() as session:
            stmt = (
                select(User.telegram_id)
                .where(User.telegram_id.is_not(None))
                .order_by(User.id)
                .limit(limit)
                .offset(offset)
            )
            result = await session.execute(stmt)
            return list(result.scalars().all())
