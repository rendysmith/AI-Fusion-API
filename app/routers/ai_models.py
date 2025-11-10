from fastapi import APIRouter, Depends, HTTPException, status, Query
from typing import List, Optional
from sqlalchemy.exc import IntegrityError

from app import schemas
from app.database.repositories.ai_model_repository import AiModelRepository
from app.dependencies import (
    get_ai_model_repository,
    get_current_admin_user
)

router = APIRouter(prefix="/ai-models", tags=["AI Models"])


@router.get(
    "/",
    response_model=List[schemas.AiModelResponse],
    summary="Get list of all AI models"
)
async def get_all_ai_models(
    category: Optional[str] = Query(None, enum=["video", "image", "text", "audio"]),
    repo: AiModelRepository = Depends(get_ai_model_repository)
):
    models = await repo.get_all_by_category(category)
    return models


@router.get(
    "/{slug}",
    response_model=schemas.AiModelResponse,
    summary="Get a specific AI model by slug"
)
async def get_ai_model_by_slug(
    slug: str,
    repo: AiModelRepository = Depends(get_ai_model_repository)
):
    model = await repo.get_by_slug(slug)
    if not model:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="AI model not found")
    return model


admin_router = APIRouter(
    prefix="/admin/ai-models",
    tags=["Admin: AI Models"],
    dependencies=[Depends(get_current_admin_user)]
)


@admin_router.post("/", response_model=schemas.AiModelResponse, status_code=status.HTTP_201_CREATED)
async def create_ai_model(
    payload: schemas.AiModelCreate,
    repo: AiModelRepository = Depends(get_ai_model_repository)
):
    try:
        return await repo.create(payload)
    except (ValueError, IntegrityError) as e:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=str(e))


@admin_router.put("/{model_id}", response_model=schemas.AiModelResponse)
async def update_ai_model(
    model_id: int,
    payload: schemas.AiModelUpdate,
    repo: AiModelRepository = Depends(get_ai_model_repository)
):
    try:
        model = await repo.update(model_id, payload)
        if not model:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="AI model not found")
        return model
    except (ValueError, IntegrityError) as e:
         raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=str(e))


@admin_router.delete("/{model_id}", response_model=dict)
async def delete_ai_model(
    model_id: int,
    repo: AiModelRepository = Depends(get_ai_model_repository)
):
    success = await repo.delete(model_id)
    if not success:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="AI model not found")
    return {"success": True}