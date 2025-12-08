from fastapi import APIRouter, Depends, HTTPException, status, Query

from app import schemas
from app.database.repositories.user_repository import UserRepository
from app.database.repositories.plan_repository import SubscriptionPlanRepository
from app.database.repositories.subscription_repository import SubscriptionRepository
from app.dependencies import (
    get_current_admin_user,
    get_user_repository,
    get_subscription_plan_repository,
    get_subscription_repository
)

admin_router = APIRouter(
    prefix="/admin/users",
    tags=["Admin: User Management"],
    dependencies=[Depends(get_current_admin_user)]
)



class PaginationParams:
    def __init__(
            self,
            page: int = Query(1, ge=1, description="Номер страницы"),
            limit: int = Query(20, ge=1, le=100, description="Объектов на странице"),
    ):
        self.page = page
        self.limit = limit


@admin_router.get(
    "",
    response_model=schemas.AdminUserListResponse,
    summary="[Admin] Get list of all users"
)
async def get_all_users(
        pagination: PaginationParams = Depends(PaginationParams),
        user_repo: UserRepository = Depends(get_user_repository)
):
    users, total = await user_repo.get_all_paginated_with_subs(
        page=pagination.page,
        limit=pagination.limit
    )


    user_responses = []
    for user in users:

        user_dto = schemas.AdminUserResponse.model_validate(user)


        if user.subscription and user.subscription.plan:
            user_dto.current_plan = user.subscription.plan

        user_responses.append(user_dto)

    return schemas.AdminUserListResponse(
        users=user_responses,
        total=total,
        page=pagination.page,
        limit=pagination.limit
    )


@admin_router.patch(
    "/{firebase_uid}/block",
    response_model=schemas.BlockUserResponse,
    summary="[Admin] Block or unblock a user"
)
async def block_user(
        firebase_uid: str,
        payload: schemas.BlockUserRequest,
        user_repo: UserRepository = Depends(get_user_repository)
):


    user = await user_repo.block_user(firebase_uid, payload.is_blocked)
    if not user:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")

    return schemas.BlockUserResponse(
        uid=user.firebase_uid,
        username=user.username,
        email=user.email,
        is_blocked=user.is_blocked,
        is_admin=user.is_admin,
        created_at=user.created_at
    )


@admin_router.patch(
    "/{firebase_uid}/subscription",
    response_model=schemas.UpdateSubscriptionResponse,
    summary="[Admin] Manually set a user's subscription"
)
async def update_user_subscription(
        firebase_uid: str,
        payload: schemas.UpdateSubscriptionRequest,
        user_repo: UserRepository = Depends(get_user_repository),
        plan_repo: SubscriptionPlanRepository = Depends(get_subscription_plan_repository),
        sub_repo: SubscriptionRepository = Depends(get_subscription_repository)
):



    user = await user_repo.get_by_firebase_uid(firebase_uid)
    if not user:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")


    plan = await plan_repo.get_by_id(payload.plan_id)
    if not plan:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Plan not found")

    subscription = await sub_repo.upsert_subscription(user, plan, payload)


    subscription.plan = plan


    subscription_dto = schemas.SubscriptionDetailResponse.model_validate(subscription)


    return schemas.UpdateSubscriptionResponse(
        subscription=subscription_dto,
        success=True
    )


@admin_router.post(
    "/bulk-credits",
    summary="[Admin] Mass add credits by Email OR Telegram ID"
)
async def add_bulk_credits(
        payload: schemas.BulkCreditRequest,
        user_repo: UserRepository = Depends(get_user_repository)
):
    success_count = 0
    failed_identifiers = []

    for item in payload.identifiers:
        clean_item = item.strip()
        if not clean_item:
            continue

        result = await user_repo.add_credits_smart(clean_item, payload.amount)

        if result:
            success_count += 1
        else:
            failed_identifiers.append(clean_item)

    return {
        "success": True,
        "processed": success_count,
        "failed_count": len(failed_identifiers),
        "failed_identifiers": failed_identifiers
    }


@admin_router.get(
    "/{user_id}",
    response_model=schemas.AdminUserFullDetailResponse,
    summary="[Admin] Get full detailed profile of a user"
)
async def get_user_detail_admin(
        user_id: int,
        user_repo: UserRepository = Depends(get_user_repository)
):
    data = await user_repo.get_user_full_details(user_id)

    if not data:
        raise HTTPException(status_code=404, detail="User not found")

    user_obj = data["user"]
    visitor_obj = data["visitor"]
    stats_dict = data["stats"]


    traffic_info = schemas.UserTrafficInfo()
    if visitor_obj:
        traffic_info = schemas.UserTrafficInfo(
            first_visit_at=visitor_obj.first_visit_at,
            utm_source=visitor_obj.utm_source,
            utm_medium=visitor_obj.utm_medium,
            utm_campaign=visitor_obj.utm_campaign,
            utm_term=visitor_obj.utm_term,
            referrer=visitor_obj.referrer
        )


    usage_stats = schemas.UserUsageStats(
        total_generations=stats_dict["total_generations"],
        successful_generations=stats_dict["successful_generations"],
        total_credits_spent=stats_dict["total_credits_spent"],
        total_money_paid=stats_dict["total_money_paid"]
    )


    return schemas.AdminUserFullDetailResponse(
        id=user_obj.id,
        firebase_uid=user_obj.firebase_uid,
        email=user_obj.email,
        username=user_obj.username,
        telegram_id=user_obj.telegram_id,
        balance=user_obj.balance,
        is_admin=user_obj.is_admin,
        is_blocked=user_obj.is_blocked,
        created_at=user_obj.created_at,
        subscription=user_obj.subscription,
        stats=usage_stats,
        traffic=traffic_info
    )