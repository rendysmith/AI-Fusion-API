import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app import schemas
from app.services.getcourse_service import GetCourseService
from app.dependencies import (
    get_getcourse_service,
    get_async_session,
    get_task_repository,
    get_current_admin_user
)
from app.database.main_models import User
from app.database.billing_models import PaymentInvoice
from app.database.subscription_models import UserSubscription, SubscriptionPlan
from app.database.task_models import GenerationTask
from app.database.repositories.task_repository import TaskRepository


admin_router = APIRouter(
    prefix="/admin/tasks",
    tags=["Admin: Tasks & Metrics"],
    dependencies=[Depends(get_current_admin_user)]
)



@admin_router.post(
    "/run-payment-check",
    summary="[CRON] Run pending payment check",

)
async def run_payment_check(
        gc_service: GetCourseService = Depends(get_getcourse_service)
):

    try:
        await gc_service.check_pending_deals()
        return {"status": "ok", "message": "Payment check executed successfully."}
    except Exception as e:
        logging.error(f"Cron /run-payment-check failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Payment check failed: {e}"
        )



@admin_router.get(
    "/generations",
    response_model=schemas.AdminGenerationListResponse,
    summary="[Admin] Get all generations (paginated)"
)
async def get_all_generations(
        page: int = Query(1, ge=1),
        limit: int = Query(50, ge=1, le=100),
        status: Optional[str] = Query(None, enum=["pending", "processing", "completed", "failed"]),
        task_repo: TaskRepository = Depends(get_task_repository)
):

    tasks_db, total = await task_repo.get_all_paginated(page, limit, status)

    generations_dto = [
        schemas.AdminGenerationTaskResponse.model_validate(task)
        for task in tasks_db
    ]

    return schemas.AdminGenerationListResponse(
        generations=generations_dto,
        total=total,
        page=page,
        limit=limit
    )


@admin_router.get(
    "/generations/{task_id}",
    response_model=schemas.AdminTaskDetailResponse,
    summary="[Admin] Get detailed info about a specific generation task"
)
async def get_task_details(
        task_id: str,
        task_repo: TaskRepository = Depends(get_task_repository)
):
    task = await task_repo.get_task_with_user(task_id)

    if not task:
        raise HTTPException(status_code=404, detail="Task not found")


    params = task.params if isinstance(task.params, dict) else {}


    prompt_text = params.get("prompt") or params.get("text_prompt") or "Без промпта"


    result_data = task.result if isinstance(task.result, dict) else {}
    video_url = result_data.get("video_url") or result_data.get("url")
    thumbnail_url = result_data.get("thumbnail_url") or result_data.get("cover_url")


    completed_at = None
    if task.status in ["completed", "failed"]:
        completed_at = task.updated_at


    return schemas.AdminTaskDetailResponse(
        id=task.id,
        status=task.status,
        model_slug=task.model_slug,
        prompt=prompt_text,

        video_url=video_url,
        thumbnail_url=thumbnail_url,
        error=task.error,

        parameters=params,

        cost=task.cost or 0.0,
        credits_used=task.cost or 0.0,

        user=task.user,

        created_at=task.created_at,
        completed_at=completed_at,
        started_at=None,

        external_task_id=task.provider_job_id
    )

@admin_router.get(
    "/metrics",
    response_model=schemas.AdminMetricsResponse,
    summary="[Admin] Get platform dashboard metrics"
)
async def get_admin_metrics(
        session: AsyncSession = Depends(get_async_session)
):


    try:
        # 1. Юзеры
        total_users = (await session.scalar(select(func.count(User.id)))) or 0
        active_subs = (await session.scalar(
            select(func.count(UserSubscription.id)).where(UserSubscription.status == 'active')
        )) or 0


        total_gens = (await session.scalar(select(func.count(GenerationTask.id)))) or 0
        gens_today = (await session.scalar(
            select(func.count(GenerationTask.id))
            .where(GenerationTask.created_at >= datetime.now(timezone.utc) - timedelta(days=1))
        )) or 0


        rev_total_cents = (await session.scalar(
            select(func.sum(PaymentInvoice.amount)).where(PaymentInvoice.status == 'paid')
        )) or 0
        rev_month_cents = (await session.scalar(
            select(func.sum(PaymentInvoice.amount))
            .where(PaymentInvoice.status == 'paid',
                   PaymentInvoice.paid_at >= datetime.now(timezone.utc) - timedelta(days=30))
        )) or 0


        model_usage_rows = (await session.execute(
            select(GenerationTask.model_slug, func.count(GenerationTask.id))
            .group_by(GenerationTask.model_slug)
        )).all()
        model_usage = {slug: count for slug, count in model_usage_rows}


        plan_dist_rows = (await session.execute(
            select(SubscriptionPlan.slug, func.count(UserSubscription.id))
            .join(SubscriptionPlan, SubscriptionPlan.id == UserSubscription.plan_id)
            .where(UserSubscription.status == 'active')
            .group_by(SubscriptionPlan.slug)
        )).all()
        plan_distribution = {slug: count for slug, count in plan_dist_rows}

        return schemas.AdminMetricsResponse(
            total_users=total_users,
            active_subscriptions=active_subs,
            total_generations=total_gens,
            generations_today=gens_today,
            revenue=schemas.RevenueMetrics(
                total=rev_total_cents / 100,
                this_month=rev_month_cents / 100,
                last_month=0
            ),
            model_usage=model_usage,
            plan_distribution=plan_distribution
        )

    except Exception as e:
        logging.error(f"Failed to calculate /admin/metrics: {e}", exc_info=True)
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, "Failed to calculate metrics")



