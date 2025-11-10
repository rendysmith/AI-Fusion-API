from fastapi import APIRouter, Depends, HTTPException, status
from typing import List
from sqlalchemy.exc import IntegrityError

from app import schemas
from app.database.repositories.plan_access_repository import PlanAccessRepository
from app.dependencies import (
    get_plan_access_repository,
    get_current_admin_user
)


admin_router = APIRouter(
    prefix="/admin/plan-model-access",
    tags=["Admin: Plan-Model Access"],
    dependencies=[Depends(get_current_admin_user)]
)

@admin_router.get(
    "",
    response_model=List[schemas.PlanModelAccessResponse],
    summary="[Admin] Get all plan-model access links"
)
async def get_all_plan_access(
    repo: PlanAccessRepository = Depends(get_plan_access_repository)
):
    return await repo.get_all()

@admin_router.post(
    "",
    response_model=schemas.PlanModelAccessResponse,
    status_code=status.HTTP_201_CREATED,
    summary="[Admin] Create a plan-model access link"
)
async def create_plan_access(
    payload: schemas.PlanModelAccessCreate,
    repo: PlanAccessRepository = Depends(get_plan_access_repository)
):

    try:

        return await repo.create(payload)
    except ValueError as e:

        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
    except IntegrityError:

        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid plan_id or model_id")

@admin_router.delete(
    "/{plan_id}/{model_id}",
    response_model=schemas.DeleteResponse,
    summary="[Admin] Remove a model from a plan"
)
async def delete_plan_access(
    plan_id: int,
    model_id: int,
    repo: PlanAccessRepository = Depends(get_plan_access_repository)
):

    success = await repo.delete_by_plan_and_model(plan_id, model_id)
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Plan-model access not found")
    return {"success": True}