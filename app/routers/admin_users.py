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


    subscription_dto = schemas.AdminSubscriptionResponse.model_validate(subscription)


    return schemas.UpdateSubscriptionResponse(
        subscription=subscription_dto,
        success=True
    )