from fastapi import APIRouter, Depends, Query
from typing import List, Optional

from app import schemas
from app.database.main_models import User
from app.dependencies import get_current_user, get_task_repository
from app.database.repositories.task_repository import TaskRepository

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
                model=task.model_name,
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