from fastapi import APIRouter, Depends, HTTPException, status
from typing import List

from app import schemas
from app.database.repositories.template_repository import TemplateRepository
from app.dependencies import (
    get_current_user,
    get_current_admin_user,
    get_template_repository
)


router = APIRouter(
    prefix="/templates",
    tags=["Templates"],
    dependencies=[Depends(get_current_user)]
)

@router.get(
    "",
    response_model=List[schemas.VideoTemplateResponse],
    summary="Get all video templates"
)
async def get_all_templates(repo: TemplateRepository = Depends(get_template_repository)):

    return await repo.get_all()


admin_router = APIRouter(
    prefix="/templates",
    tags=["Admin: Templates"],
    dependencies=[Depends(get_current_admin_user)]
)

@admin_router.post(
    "",
    response_model=schemas.VideoTemplateResponse,
    status_code=status.HTTP_201_CREATED
)
async def create_template(
    payload: schemas.VideoTemplateCreate,
    repo: TemplateRepository = Depends(get_template_repository)
):

    return await repo.create(payload)

@admin_router.put(
    "/{template_id}",
    response_model=schemas.VideoTemplateResponse
)
async def update_template(
    template_id: int,
    payload: schemas.VideoTemplateUpdate,
    repo: TemplateRepository = Depends(get_template_repository)
):

    template = await repo.update(template_id, payload)
    if not template:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Template not found")
    return template

@admin_router.delete(
    "/{template_id}",
    response_model=schemas.DeleteResponse
)
async def delete_template(
    template_id: int,
    repo: TemplateRepository = Depends(get_template_repository)
):

    success = await repo.delete(template_id)
    if not success:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Template not found")
    return {"success": True}