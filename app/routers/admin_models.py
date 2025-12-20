from fastapi import APIRouter, Depends, HTTPException, status
from typing import List

from app import schemas
from app.dependencies import (
    get_current_admin_user,
    get_ai_model_repository, get_priority_repository
)
from app.database.repositories.ai_model_repository import AiModelRepository
from app.database.repositories.priority_model_repository import PriorityModelRepository

admin_router = APIRouter(
    prefix="/admin",
    tags=["Admin: Models & Routing"],
    dependencies=[Depends(get_current_admin_user)]
)



@admin_router.get("/storefront", response_model=List[schemas.AiModelResponse])
async def get_storefront_models(repo: AiModelRepository = Depends(get_ai_model_repository)):
    """Получить все модели (которые видит юзер)"""
    return await repo.get_all_by_category(None)

@admin_router.post("/storefront", response_model=schemas.AiModelResponse)
async def create_storefront_model(
    payload: schemas.AiModelCreate,
    repo: AiModelRepository = Depends(get_ai_model_repository)
):
    """Добавить новую модель в витрину"""
    return await repo.create(payload)

@admin_router.put("/storefront/{model_id}", response_model=schemas.AiModelResponse)
async def update_storefront_model(
    model_id: int,
    payload: schemas.AiModelUpdate,
    repo: AiModelRepository = Depends(get_ai_model_repository)
):
    """Обновить (включить/выключить, изменить цену)"""
    return await repo.update(model_id, payload)

@admin_router.delete("/storefront/{model_id}")
async def delete_storefront_model(
    model_id: int,
    repo: AiModelRepository = Depends(get_ai_model_repository)
):
    """Удалить модель из витрины"""
    success = await repo.delete(model_id)
    if not success:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Model not found")
    return {"success": True}


@admin_router.get("/routing", response_model=List[schemas.BackendResponse])
async def get_routing_rules(repo: PriorityModelRepository = Depends(get_priority_repository)):
    """Посмотреть все настройки провайдеров"""
    return await repo.get_all_backends()

@admin_router.post("/routing", response_model=schemas.BackendResponse)
async def create_routing_rule(
    payload: schemas.BackendCreate,
    repo: PriorityModelRepository = Depends(get_priority_repository)
):
    """
    Добавить провайдера для модели.
    Пример: model_name='gpt-4o', provider='Grsai', priority=2
    """
    return await repo.create_backend(payload)

@admin_router.put("/routing/{backend_id}", response_model=schemas.BackendResponse)
async def update_routing_rule(
    backend_id: int,
    payload: schemas.BackendUpdate,
    repo: PriorityModelRepository = Depends(get_priority_repository)
):
    """Изменить приоритет или провайдера"""
    updated = await repo.update_backend(backend_id, payload)
    if not updated:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Rule not found")
    return updated

@admin_router.delete("/routing/{backend_id}")
async def delete_routing_rule(
    backend_id: int,
    repo: PriorityModelRepository = Depends(get_priority_repository)
):
    """Удалить правило маршрутизации"""
    success = await repo.delete_backend(backend_id)
    if not success:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Rule not found")
    return {"success": True}