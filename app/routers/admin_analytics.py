from datetime import date, datetime, time

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.billing_models import PaymentInvoice
from app.database.main_models import User
from app.database.repositories.metric_repository import VisitorRepository
from app.dependencies import get_visitor_repository, get_current_admin_user, get_async_session

admin_router = APIRouter(
    prefix="/admin/analytics",
    tags=["Admin: Analytics"],
    dependencies=[Depends(get_current_admin_user)]
)

@admin_router.get("/daily-funnel")
async def get_daily_funnel(
    date_from: date = Query(...),
    date_to: date = Query(...),
    visitor_repo: VisitorRepository = Depends(get_visitor_repository),
    session: AsyncSession = Depends(get_async_session)
):

    traffic_stats = await visitor_repo.get_traffic_stats(date_to)

    start_dt = datetime.combine(date_from, time.min)
    end_dt = datetime.combine(date_to, time.max)


    stmt_bots = select(func.count(User.id)).where(
        User.telegram_id.isnot(None),
        User.created_at.between(start_dt, end_dt)
    )
    bot_signups = (await session.scalar(stmt_bots)) or 0


    stmt_paid = select(func.count(PaymentInvoice.id)).where(
        PaymentInvoice.status == 'paid',
        PaymentInvoice.created_at.between(start_dt, end_dt)
    )
    total_sales = (await session.scalar(stmt_paid)) or 0

    return {
        "period": {
            "from": date_from,
            "to": date_to
        },
        "traffic": {
            "total": traffic_stats["total_visitors"],
            "new": traffic_stats["new_visitors"],
            "returning": traffic_stats["returning_visitors"]
        },
        "bot_signups": bot_signups,
        "sales_count": total_sales
    }