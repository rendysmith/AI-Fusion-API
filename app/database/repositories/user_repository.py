from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sqlalchemy.orm import selectinload
from sqlalchemy.future import select

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
            stmt = select(User).where(User.firebase_uid == uid)
            result = await session.execute(stmt)
            return result.scalars().first()

    async def get_by_telegram_id(self, telegram_id: int) -> User | None:
        async with self.session_factory() as session:
            stmt = select(User).where(User.telegram_id == telegram_id)
            result = await session.execute(stmt)
            return result.scalars().first()

    async def get_or_create_by_firebase_uid(self, uid: str, email: str | None) -> User:

        async with self.session_factory() as session:

            stmt = select(User).where(User.firebase_uid == uid)
            result = await session.execute(stmt)
            user = result.scalars().first()

            if user:
                return user


            user = User(
                firebase_uid=uid,
                email=email,
                coefficient=1.0
            )
            session.add(user)
            await session.commit()
            await session.refresh(user)
            return user

    async def link_telegram_id(self, user_id: int, telegram_id: int) -> User:

        async with self.session_factory() as session:
            stmt = update(User).where(User.id == user_id) \
                .values(telegram_id=telegram_id) \
                .returning(User)

            result = await session.execute(stmt)
            await session.commit()
            return result.scalars().one()

    async def create_user_for_telegram(self, uid: str, email: str, telegram_id: int) -> User:

        async with self.session_factory() as session:
            new_user = User(
                firebase_uid=uid,
                email=email,
                telegram_id=telegram_id,
                coefficient=1.0
            )
            session.add(new_user)
            await session.commit()
            await session.refresh(new_user)
            return new_user

    async def link_firebase_uid(self, user_id: int, uid: str, email: str):

        async with self.session_factory() as session:
            stmt = update(User).where(User.id == user_id) \
                .values(firebase_uid=uid, email=email)
            await session.execute(stmt)
            await session.commit()

    async def deduct_balance(self, user_id: int, amount: float) -> bool:

        async with self.session_factory() as session:
            stmt = (
                update(User)
                .where(
                    User.id == user_id,
                    User.balance >= amount
                )
                .values(balance=User.balance - amount)
            )
            result = await session.execute(stmt)
            await session.commit()

            return result.rowcount > 0

    async def refund_balance(self, user_id: int, amount: float):

        async with self.session_factory() as session:
            stmt = (
                update(User)
                .where(User.id == user_id)
                .values(balance=User.balance + amount)
            )
            await session.execute(stmt)
            await session.commit()