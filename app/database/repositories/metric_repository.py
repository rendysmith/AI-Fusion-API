from datetime import datetime
from uuid import UUID
from typing import Optional

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sqlalchemy.dialects.postgresql import insert

# Импортируйте вашу модель Visitor
from app.database.metric_models import Visitor


class VisitorRepository:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]):
        self.session_factory = session_factory

    async def track_visit(self, visitor_id: UUID, referrer: Optional[str] = None, user_agent: Optional[str] = None):
        """
        UPSERT: Создает гостя или обновляет время последнего визита.
        """
        async with self.session_factory() as session:
            stmt = insert(Visitor).values(
                visitor_id=visitor_id,
                referrer=referrer,
                user_agent=user_agent,
                last_visit_at=datetime.now(),
                # first_visit_at заполнится сам (default now)
            )

            # Если такой ID есть, обновляем только last_visit_at
            stmt = stmt.on_conflict_do_update(
                index_elements=[Visitor.visitor_id],
                set_={"last_visit_at": datetime.now()}
            )

            await session.execute(stmt)
            await session.commit()

    async def link_user(self, visitor_id: UUID, user_id: int):
        """
        КОНВЕРСИЯ: Привязывает анонимного visitor_id к реальному user_id.
        """
        async with self.session_factory() as session:
            stmt = (
                update(Visitor)
                .where(Visitor.visitor_id == visitor_id)
                .values(user_id=user_id)
            )
            await session.execute(stmt)
            await session.commit()