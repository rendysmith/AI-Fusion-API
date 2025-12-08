from datetime import date, datetime, timedelta, timezone
from typing import Optional, Dict, Any, List, Tuple

from sqlalchemy import select, func, desc
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from app.database.analytics_models import DailySystemStats, UserModelStats, CompletedTaskLog
from app.database.main_models import User
from app.database.metric_models import Visitor


class AnalyticsRepository:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]):
        self.session_factory = session_factory

    async def log_and_update_stats_on_completion(
            self, task_id: str, user_id: int, model_slug: str,
            cost: float, prime_cost: float, created_at: datetime
    ):

        async with self.session_factory() as session:

            log_entry = CompletedTaskLog(
                task_mongo_id=task_id, user_id=user_id,
                model_slug=model_slug, cost=cost, prime_cost=prime_cost, created_at=created_at
            )
            session.add(log_entry)


            today = created_at.date()
            profit = cost - prime_cost
            stmt_daily = pg_insert(DailySystemStats).values(
                date=today, tasks_completed=1, total_revenue=cost,
                total_prime_cost=prime_cost, profit=profit
            )
            stmt_daily_upsert = stmt_daily.on_conflict_do_update(
                index_elements=['date'],
                set_={
                    'tasks_completed': DailySystemStats.tasks_completed + 1,
                    'total_revenue': DailySystemStats.total_revenue + stmt_daily.excluded.total_revenue,
                    'total_prime_cost': DailySystemStats.total_prime_cost + stmt_daily.excluded.total_prime_cost,
                    'profit': DailySystemStats.profit + stmt_daily.excluded.profit
                }
            )
            await session.execute(stmt_daily_upsert)

            stmt_user_model = pg_insert(UserModelStats).values(
                user_id=user_id, model_slug = model_slug,
                total_tasks_completed=1, total_spending=cost
            )
            stmt_user_model_upsert = stmt_user_model.on_conflict_do_update(
                index_elements = ['user_id', 'model_slug'],
                set_={
                    'total_tasks_completed': UserModelStats.total_tasks_completed + 1,
                    'total_spending': UserModelStats.total_spending + stmt_user_model.excluded.total_spending
                }
            )
            await session.execute(stmt_user_model_upsert)

            await session.commit()


    async def get_detailed_activity(self, start_time: datetime, end_time: datetime):

        async with self.session_factory() as session:
            stmt = select(CompletedTaskLog).where(
                CompletedTaskLog.created_at.between(start_time, end_time)
            )

            result = await session.execute(stmt)
            return result.scalars().all()

    async def get_completed_tasks_count_for_period(self, hours: int) -> int:
        async with self.session_factory() as session:
            time_ago = datetime.now(timezone.utc) - timedelta(hours=hours)
            stmt = select(func.count(CompletedTaskLog.id)).where(
                CompletedTaskLog.created_at >= time_ago
            )
            result = await session.scalar(stmt)
            return result or 0

    async def get_overall_model_usage(self):
        async with self.session_factory() as session:
            stmt = select(
                UserModelStats.model_slug,
                func.sum(UserModelStats.total_tasks_completed).label('usage_count')
            ).group_by(UserModelStats.model_slug).order_by(func.sum(UserModelStats.total_tasks_completed).desc())
            result = await session.execute(stmt)
            return result.all()

    async def get_profitability_for_period(self, start_date: date, end_date: date):
        async with self.session_factory() as session:
            stmt = select(DailySystemStats).where(
                DailySystemStats.date.between(start_date, end_date)
            ).order_by(DailySystemStats.date.asc())
            result = await session.execute(stmt)
            return result.scalars().all()


    async def create_usage_report(self, start_date: date, end_date: date) -> Dict[str, Any]:
        async with self.session_factory() as session:

            start_dt = datetime.combine(start_date, datetime.min.time(), tzinfo=timezone.utc)
            end_dt = datetime.combine(end_date, datetime.max.time(), tzinfo=timezone.utc)


            where_clause = [CompletedTaskLog.created_at.between(start_dt, end_dt)]


            profit_stmt = select(
                func.sum(CompletedTaskLog.cost).label('total_revenue'),
                func.sum(CompletedTaskLog.prime_cost).label('total_prime_cost')
            ).where(*where_clause)

            profit_result = (await session.execute(profit_stmt)).first()
            total_profit = (profit_result.total_revenue or 0) - (profit_result.total_prime_cost or 0)


            model_usage_stmt = select(
                CompletedTaskLog.model_slug,
                func.count().label('count')
            ).where(*where_clause).group_by(CompletedTaskLog.model_slug).order_by(func.count().desc())

            model_usage_result = (await session.execute(model_usage_stmt)).all()

            return {
                "total_profit": total_profit,
                "model_usage": model_usage_result
            }

    async def get_user_summary(self, user_id: int) -> Dict[str, Any]:
        async with self.session_factory() as session:
            stmt = select(
                func.sum(UserModelStats.total_spending).label("total_spending"),
                func.sum(UserModelStats.total_tasks_completed).label("total_tasks")
            ).where(UserModelStats.user_id == user_id)

            summary = (await session.execute(stmt)).first()

            model_usage_stmt = select(
                UserModelStats.model_slug,
                func.sum(UserModelStats.total_tasks_completed).label("count")
            ).where(UserModelStats.user_id == user_id).group_by(UserModelStats.model_slug)


            model_usage = (await session.execute(model_usage_stmt)).all()

            return {
                "total_spending": summary.total_spending or 0.0,
                "total_tasks": summary.total_tasks or 0,
                "model_usage": model_usage
            }

    async def get_analytics_report(
            self,
            start_date: date,
            end_date: date,
            user_id: Optional[int] = None,
            model_name: Optional[str] = None
    ) -> Dict[str, Any]:
        async with self.session_factory() as session:
            start_dt = datetime.combine(start_date, datetime.min.time(), tzinfo=timezone.utc)
            end_dt = datetime.combine(end_date, datetime.max.time(), tzinfo=timezone.utc)


            query = select(CompletedTaskLog).where(
                CompletedTaskLog.created_at.between(start_dt, end_dt)
            )
            if user_id:
                query = query.where(CompletedTaskLog.user_id == user_id)
            if model_name:
                query = query.where(CompletedTaskLog.model_slug == model_name)


            report_subquery = query.subquery()


            summary_stmt = select(
                func.count().label("total_generations"),
                func.sum(report_subquery.c.cost).label("total_revenue"),
                func.sum(report_subquery.c.prime_cost).label("total_prime_cost")
            ).select_from(report_subquery)

            summary_result = (await session.execute(summary_stmt)).first()


            model_breakdown_stmt = select(
                report_subquery.c.model_slug,
                func.count().label("count"),
                func.sum(report_subquery.c.cost).label("revenue")
            ).select_from(report_subquery).group_by(report_subquery.c.model_name).order_by(func.count().desc())

            model_breakdown_result = (await session.execute(model_breakdown_stmt)).all()

            total_revenue = summary_result.total_revenue or 0
            total_prime_cost = summary_result.total_prime_cost or 0

            return {
                "total_generations": summary_result.total_generations or 0,
                "total_revenue": total_revenue,
                "total_profit": total_revenue - total_prime_cost,
                "model_breakdown": model_breakdown_result
            }

    async def get_daily_activity(
            self,
            user_id: Optional[int] = None,
    ) -> List:
        async with self.session_factory() as session:

            end_date = date.today()
            start_date = end_date - timedelta(days=30)


            stmt = (
                select(
                    func.date(CompletedTaskLog.created_at).label('date'),
                    func.count().label('count')
                )
                .where(func.date(CompletedTaskLog.created_at).between(start_date, end_date))
            )

            if user_id:
                stmt = stmt.where(CompletedTaskLog.user_id == user_id)

            stmt = stmt.group_by(func.date(CompletedTaskLog.created_at)).order_by(
                func.date(CompletedTaskLog.created_at).asc())

            result = await session.execute(stmt)
            return result.all()

    async def get_users_with_sources(
            self,
            page: int,
            limit: int,
            date_from: Optional[date] = None,
            date_to: Optional[date] = None,
            utm_source: Optional[str] = None,
            employee_tag: Optional[str] = None
    ) -> Tuple[List[Any], int]:

        offset = (page - 1) * limit

        async with self.session_factory() as session:

            query = select(
                User.id.label("user_id"),
                User.email,
                User.username,
                User.created_at,
                Visitor.utm_source,
                Visitor.utm_medium,
                Visitor.utm_campaign,
                Visitor.utm_term,
                Visitor.referrer
            ).join(
                Visitor, Visitor.user_id == User.id, isouter=True
            ).order_by(User.created_at.desc())


            if date_from and date_to:
                start_dt = datetime.combine(date_from, datetime.min.time(), tzinfo=timezone.utc)
                end_dt = datetime.combine(date_to, datetime.max.time(), tzinfo=timezone.utc)
                query = query.where(User.created_at.between(start_dt, end_dt))


            if utm_source:
                query = query.where(Visitor.utm_source == utm_source)


            if employee_tag:

                query = query.where(Visitor.utm_term.ilike(f"%{employee_tag}%"))


            count_stmt = select(func.count()).select_from(query.subquery())
            total = await session.scalar(count_stmt) or 0


            query = query.limit(limit).offset(offset)

            result = await session.execute(query)
            rows = result.all()

            return rows, total

    async def get_raw_visitors_log(
            self,
            page: int,
            limit: int,
            date_from: Optional[date] = None,
            date_to: Optional[date] = None
    ) -> Tuple[List[Visitor], int]:

        offset = (page - 1) * limit
        async with self.session_factory() as session:

            stmt = select(Visitor).order_by(desc(Visitor.first_visit_at))


            if date_from and date_to:
                start_dt = datetime.combine(date_from, datetime.min.time(), tzinfo=timezone.utc)
                end_dt = datetime.combine(date_to, datetime.max.time(), tzinfo=timezone.utc)
                stmt = stmt.where(Visitor.first_visit_at.between(start_dt, end_dt))


            count_stmt = select(func.count()).select_from(stmt.subquery())
            total = await session.scalar(count_stmt) or 0


            stmt = stmt.limit(limit).offset(offset)
            result = await session.execute(stmt)

            return result.scalars().all(), total