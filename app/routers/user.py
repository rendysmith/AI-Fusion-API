import logging
from datetime import datetime

from fastapi import APIRouter, Depends, Query, Request, Header, HTTPException
from typing import List, Optional

from starlette import status

from app import schemas
from app.database.main_models import User
from app.database.repositories.plan_repository import SubscriptionPlanRepository
from app.database.repositories.subscription_repository import SubscriptionRepository
from app.database.repositories.user_repository import UserRepository
from app.dependencies import get_current_user, get_task_repository, get_user_repository, \
    get_subscription_plan_repository, get_subscription_repository
from app.database.repositories.task_repository import TaskRepository
from app.services.firebase_service import verify_firebase_token

router = APIRouter(prefix="/user", tags=["User"])



class PaginationParams:

    def __init__(
            self,
            page: int = Query(1, ge=1, description="Номер страницы"),
            limit: int = Query(20, ge=1, le=100, description="Объектов на странице"),
    ):
        self.page = page
        self.limit = limit



@router.get("/generations", response_model=schemas.GenerationHistoryResponse)
async def get_user_generations_history(
        user: User = Depends(get_current_user),
        pagination: PaginationParams = Depends(PaginationParams),
        model_name: Optional[str] = Query(None, description="Фильтр по названию модели"),
        task_repo: TaskRepository = Depends(get_task_repository),
):



    tasks, total = await task_repo.get_tasks_by_user_id_paginated(
        user_id=user.id, page=pagination.page, limit=pagination.limit, model_name=model_name
    )


    generations_list: List[schemas.GenerationHistoryItem] = []
    for task in tasks:
        params = task.params if isinstance(task.params, dict) else {}
        result = task.result if isinstance(task.result, dict) else {}

        generations_list.append(
            schemas.GenerationHistoryItem(
                task_id=task.id,
                prompt=params.get("prompt"),
                model=task.model_slug,
                status=task.status,
                error=task.error,
                created_at=task.created_at,
                parameters=params,
                result=schemas.GenerationResultModel(

                    videoUrl=result.get("video_url") or result.get("url"),
                    thumbnailUrl=result.get("video_url")
                )
            )
        )

    return schemas.GenerationHistoryResponse(
        generations=generations_list,
        total=total,
        page=pagination.page,
        limit=pagination.limit,
    )



@router.get("/balance", response_model=schemas.UserBalanceResponse)
async def get_user_balance(
        user: User = Depends(get_current_user),
):

    return schemas.UserBalanceResponse(
        balance=float(user.balance),
        plan="pro",
        generations_left=50
    )


@router.get("/profile", response_model=schemas.UserProfileResponse)
async def get_user_profile(
        user: User = Depends(get_current_user)
):

    plan = schemas.PlanSchema(id=1, name="Free", slug="free", generationsPerMonth=10)
    sub = schemas.SubscriptionSchema(status="active", currentPeriodEnd=datetime.now())

    return schemas.UserProfileResponse(
        uid=user.firebase_uid,
        email=user.email,
        username=user.username,
        display_name=user.display_name,
        photo_url=user.photo_url,
        balance=float(user.balance),
        is_admin=user.is_admin,
        current_plan=plan,
        subscription=sub,
        telegram_id=user.telegram_id,
        telegram_username=None,
    )



@router.put("/profile", response_model=schemas.UserProfileResponse)
async def create_or_update_user_profile(
        payload: schemas.UserProfileUpdateRequest,
        request: Request,
        user_repo: UserRepository = Depends(get_user_repository),
        plan_repo: SubscriptionPlanRepository = Depends(get_subscription_plan_repository),
        sub_repo: SubscriptionRepository = Depends(get_subscription_repository),
        authorization: str = Header(...)
):

    try:

        token = authorization.split("Bearer ")[1]
        decoded_token = verify_firebase_token(token)
        firebase_uid = decoded_token.get("uid")
        email = decoded_token.get("email")
        if not firebase_uid:
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid token")

    except Exception:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid token")

    existing_user = await user_repo.get_by_firebase_uid(firebase_uid)


    if payload.username:
        if existing_user and existing_user.firebase_uid != firebase_uid:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Username '{payload.username}' already taken."
            )


    try:
        user = await user_repo.create_or_update_profile(
            firebase_uid=firebase_uid,
            email=email,
            payload=payload
        )
    except Exception as e:
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, f"DB error: {e}")

    if existing_user is None:
        logging.info(f"New user detected (UID: {firebase_uid}). Assigning 'free' plan.")

        free_plan = await plan_repo.get_by_slug("free")

        if free_plan:
            try:

                await sub_repo.create_default_subscription(user, free_plan)

                await user_repo.session_factory().refresh(user)

                logging.info(f"Assigned 'free' plan with {free_plan.credits_granted} credits.")
            except Exception as e:
                logging.error(f"Failed to assign default subscription for user {firebase_uid}: {e}")
        else:
            logging.warning("Could not find 'free' plan in database to assign to new user.")

    subscription = await sub_repo.get_active_subscription_by_user_id(user.id)
    current_plan = None
    if subscription:

        current_plan = await plan_repo.get_by_id(subscription.plan_id)


    return schemas.UserProfileResponse(
        uid=user.firebase_uid,
        email=user.email,
        username=user.username,
        display_name=user.display_name,
        photo_url=user.photo_url,
        balance=float(user.balance),
        is_admin=user.is_admin,
        current_plan=current_plan,
        subscription=subscription,
        telegram_id=user.telegram_id
    )


@router.get("/is-admin", response_model=schemas.IsAdminResponse)
async def check_if_user_is_admin(
    user: User = Depends(get_current_user)
):

    return {"is_admin": user.is_admin}