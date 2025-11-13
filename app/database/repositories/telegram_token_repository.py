from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from datetime import datetime
from typing import Optional

from app.database.main_models import TelegramAuthToken

class TelegramTokenRepository:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]):
        self.session_factory = session_factory

    async def create_token(self, token: str, firebase_uid: str, expires_at: datetime):
        async with self.session_factory() as session:
            new_token = TelegramAuthToken(
                token=token,
                firebase_uid=firebase_uid,
                expires_at=expires_at,
                status='pending'
            )
            session.add(new_token)
            await session.commit()

    async def get_token(self, token: str) -> Optional[TelegramAuthToken]:
        async with self.session_factory() as session:
            return await session.get(TelegramAuthToken, token)

    async def complete_token(self, token: str, telegram_id: int, telegram_username: Optional[str]):
        async with self.session_factory() as session:
            stmt = (
                update(TelegramAuthToken)
                .where(TelegramAuthToken.token == token)
                .values(
                    status='completed',
                    telegram_id=telegram_id,
                    telegram_username=telegram_username,
                )
            )
            await session.execute(stmt)
            await session.commit()