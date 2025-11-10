from datetime import datetime

from fastapi import APIRouter, Depends, Query, Request, Header, HTTPException
from typing import List, Optional

from starlette import status

from app import schemas
from app.database.main_models import User
from app.database.repositories.user_repository import UserRepository
from app.dependencies import get_current_user, get_task_repository, get_user_repository
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


    if payload.username:
        existing_user = await user_repo.get_by_username(payload.username)
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
        telegram_id=user.telegram_id
    )