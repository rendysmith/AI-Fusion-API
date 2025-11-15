import asyncio
import logging
from datetime import datetime, timezone, timedelta

from fastapi import APIRouter, Depends, Query, Request, Header, HTTPException
from typing import List, Optional

from starlette import status

from app import schemas
from app.database.main_models import User
from app.database.repositories.plan_access_repository import PlanAccessRepository
from app.database.repositories.plan_repository import SubscriptionPlanRepository
from app.database.repositories.subscription_repository import SubscriptionRepository
from app.database.repositories.user_repository import UserRepository
from app.dependencies import get_current_user, get_task_repository, get_user_repository, \
    get_subscription_plan_repository, get_subscription_repository, get_plan_access_repository
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

@router.get("/profile", response_model=schemas.UserProfileResponse)
async def get_user_profile(
        user: User = Depends(get_current_user)
):

    return schemas.UserProfileResponse.model_validate(user)


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
        decoded_token = await asyncio.to_thread(verify_firebase_token, token)

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

                await user_repo.session_factory().refresh(user, attribute_names=['balance', 'subscription'])
            except Exception as e:
                logging.error(f"Failed to assign default subscription...: {e}")
        else:
            logging.warning("Could not find 'free' plan...")

    user_with_plan = await user_repo.get_by_firebase_uid(user.firebase_uid)

    return schemas.UserProfileResponse.model_validate(user_with_plan)


@router.get("/is-admin", response_model=schemas.IsAdminResponse)
async def check_if_user_is_admin(
    user: User = Depends(get_current_user)
):

    return {"is_admin": user.is_admin}


@router.get(
    "/subscription",
    response_model=schemas.UserSubscriptionDetailResponse,
    summary="Get user's current subscription details"
)
async def get_user_subscription(
        user: User = Depends(get_current_user),
        sub_repo: SubscriptionRepository = Depends(get_subscription_repository),
        plan_access_repo: PlanAccessRepository = Depends(get_plan_access_repository),
        task_repo: TaskRepository = Depends(get_task_repository)
):

    subscription = user.subscription
    plan = user.subscription.plan if user.subscription else None

    available_models_list = []
    if plan:

        models = await plan_access_repo.get_models_for_plan(plan.id)

        available_models_list = [schemas.AvailableModel.model_validate(m) for m in models]
    else:

        pass




    processing_count = await task_repo.get_processing_task_count(user.id)


    time_24_hours_ago = datetime.now(timezone.utc) - timedelta(days=1)
    today_count = await task_repo.get_tasks_count_since(user.id, time_24_hours_ago)

    usage = schemas.SubscriptionUsage(
        today=today_count,
        concurrent=processing_count
    )

    return schemas.UserSubscriptionDetailResponse(
        plan=plan,
        available_models=available_models_list,
        usage=usage
    )