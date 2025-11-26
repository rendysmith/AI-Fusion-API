from datetime import datetime, date, time
from uuid import UUID
from typing import Optional

from sqlalchemy import select, update, func, and_
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sqlalchemy.dialects.postgresql import insert

# Импортируйте вашу модель Visitor
from app.database.metric_models import Visitor


class VisitorRepository:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]):
        self.session_factory = session_factory

    async def track_visit(self, visitor_id: UUID, referrer: Optional[str] = None, user_agent: Optional[str] = None):

        async with self.session_factory() as session:
            stmt = insert(Visitor).values(
                visitor_id=visitor_id,
                referrer=referrer,
                user_agent=user_agent,
                last_visit_at=datetime.now(),

            )

            stmt = stmt.on_conflict_do_update(
                index_elements=[Visitor.visitor_id],
                set_={"last_visit_at": datetime.now()}
            )

            await session.execute(stmt)
            await session.commit()

    async def link_user(self, visitor_id: UUID, user_id: int):

        async with self.session_factory() as session:
            stmt = (
                update(Visitor)
                .where(Visitor.visitor_id == visitor_id)
                .values(user_id=user_id)
            )
            await session.execute(stmt)
            await session.commit()

    async def get_traffic_stats(self, start_date: date, end_date: date):
        async with self.session_factory() as session:

            start_dt = datetime.combine(start_date, time.min)
            end_dt = datetime.combine(end_date, time.max)

            stmt = select(

                func.count(Visitor.visitor_id).filter(
                    Visitor.last_visit_at.between(start_dt, end_dt)
                ).label("total_visits"),


                func.count(Visitor.visitor_id).filter(
                    Visitor.first_visit_at.between(start_dt, end_dt)
                ).label("new_visits"),


                func.count(Visitor.visitor_id).filter(
                    and_(
                        Visitor.last_visit_at.between(start_dt, end_dt),
                        Visitor.first_visit_at < start_dt
                    )
                ).label("returning_visits")
            )

            result = await session.execute(stmt)
            row = result.one()

            return {
                "total_visitors": row.total_visits or 0,
                "new_visitors": row.new_visits or 0,
                "returning_visitors": row.returning_visits or 0
            }