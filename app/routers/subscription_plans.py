from fastapi import APIRouter, Depends, HTTPException, status
from typing import List
from sqlalchemy.exc import IntegrityError

from app import schemas
from app.database.repositories.plan_repository import SubscriptionPlanRepository
from app.dependencies import (
    get_subscription_plan_repository,
    get_current_admin_user
)




router = APIRouter(
    prefix="/subscription-plans",
    tags=["Subscription Plans"]
)

@router.get(
    "",
    response_model=List[schemas.SubscriptionPlanResponse],
    summary="Get all ACTIVE subscription plans"
)
async def get_public_subscription_plans(
    repo: SubscriptionPlanRepository = Depends(get_subscription_plan_repository)
):
    """(GET /subscription-plans)
    Получить список всех АКТИВНЫХ планов для витрины.
    """

    return await repo.get_all(only_active=True)


admin_router = APIRouter(
    prefix="/admin/subscription-plans",
    tags=["Admin: Subscription Plans"],
    dependencies=[Depends(get_current_admin_user)]
)

@admin_router.get(
    "",
    response_model=List[schemas.SubscriptionPlanResponse],
    summary="[Admin] Get list of all plans"
)
async def get_all_subscription_plans(
    repo: SubscriptionPlanRepository = Depends(get_subscription_plan_repository)
):

    return await repo.get_all(only_active=False)

@admin_router.post(
    "",
    response_model=schemas.SubscriptionPlanResponse,
    status_code=status.HTTP_201_CREATED,
    summary="[Admin] Create a new plan"
)
async def create_subscription_plan(
    payload: schemas.SubscriptionPlanCreate,
    repo: SubscriptionPlanRepository = Depends(get_subscription_plan_repository)
):

    try:
        return await repo.create(payload)
    except (ValueError, IntegrityError) as e:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=str(e))

@admin_router.put(
    "/{plan_id}",
    response_model=schemas.SubscriptionPlanResponse,
    summary="[Admin] Update a plan"
)
async def update_subscription_plan(
    plan_id: int,
    payload: schemas.SubscriptionPlanUpdate,
    repo: SubscriptionPlanRepository = Depends(get_subscription_plan_repository)
):

    try:
        plan = await repo.update(plan_id, payload)
        if not plan:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Subscription plan not found")
        return plan
    except (ValueError, IntegrityError) as e:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=str(e))

@admin_router.delete(
    "/{plan_id}",
    response_model=schemas.DeleteResponse,
    summary="[Admin] Delete a plan"
)
async def delete_subscription_plan(
    plan_id: int,
    repo: SubscriptionPlanRepository = Depends(get_subscription_plan_repository)
):
    try:
        success = await repo.delete(plan_id)
        if not success:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Subscription plan not found")
        return {"success": True}
    except ValueError as e:

        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=str(e))