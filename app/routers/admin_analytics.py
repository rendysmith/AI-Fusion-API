from datetime import date, datetime, time, timezone

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.billing_models import PaymentInvoice
from app.database.main_models import User
from app.database.repositories.metric_repository import VisitorRepository
from app.dependencies import get_visitor_repository, get_current_admin_user, get_async_session
from app.schemas import AnalyticsDailyResponse, AnalyticsVisitors

admin_router = APIRouter(
    prefix="/admin/analytics",
    tags=["Admin: Analytics"],
    dependencies=[Depends(get_current_admin_user)]
)


@admin_router.get("/daily-funnel", response_model=AnalyticsDailyResponse)
async def get_daily_funnel(
        date_from: date = Query(...),
        date_to: date = Query(...),
        visitor_repo: VisitorRepository = Depends(get_visitor_repository),
        session: AsyncSession = Depends(get_async_session)
):

    traffic_stats = await visitor_repo.get_traffic_stats(date_from, date_to)

    visitors_total = traffic_stats["total_visitors"]
    visitors_new = traffic_stats["new_visitors"]
    visitors_repeat = traffic_stats["returning_visitors"]

    start_dt = datetime.combine(date_from, time.min, tzinfo=timezone.utc)
    end_dt = datetime.combine(date_to, time.max, tzinfo=timezone.utc)


    stmt_bots = select(func.count(User.id)).where(
        User.telegram_id.isnot(None),
        User.created_at.between(start_dt, end_dt)
    )
    telegram_signups = (await session.scalar(stmt_bots)) or 0


    stmt_paid = select(func.count(PaymentInvoice.id)).where(
        PaymentInvoice.status == 'paid',
        PaymentInvoice.created_at.between(start_dt, end_dt)
    )
    purchases = (await session.scalar(stmt_paid)) or 0




    if visitors_total > 0:
        conv_vis_to_sign = (telegram_signups / visitors_total) * 100
    else:
        conv_vis_to_sign = 0.0


    if telegram_signups > 0:
        conv_sign_to_pur = (purchases / telegram_signups) * 100
    else:
        conv_sign_to_pur = 0.0


    if visitors_total > 0:
        conv_overall = (purchases / visitors_total) * 100
    else:
        conv_overall = 0.0

    return AnalyticsDailyResponse(
        visitors=AnalyticsVisitors(
            total=visitors_total,
            new=visitors_new,
            repeat=visitors_repeat
        ),
        telegram_signups=telegram_signups,
        purchases=purchases,
        conversion_visitors_to_signups=round(conv_vis_to_sign, 2),
        conversion_signups_to_purchases=round(conv_sign_to_pur, 2),
        conversion_overall=round(conv_overall, 2)
    )