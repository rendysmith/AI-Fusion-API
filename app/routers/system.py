from fastapi import APIRouter, Depends
from pydantic import BaseModel
from app.dependencies import get_system_repository, get_current_admin_user
from app.database.repositories.system_repository import SystemRepository

router = APIRouter(prefix="/system", tags=["System"])

class MaintenanceStatusResponse(BaseModel):
    is_maintenance: bool
    message: str | None

class MaintenanceToggleRequest(BaseModel):
    enabled: bool
    message: str = "Ведутся технические работы. Генерация временно недоступна."


@router.get("/status", response_model=MaintenanceStatusResponse)
async def get_system_status(
    repo: SystemRepository = Depends(get_system_repository)
):
    is_maint, msg = await repo.is_maintenance_mode()
    return MaintenanceStatusResponse(is_maintenance=is_maint, message=msg if is_maint else None)


@router.post("/maintenance", dependencies=[Depends(get_current_admin_user)])
async def toggle_maintenance(
    payload: MaintenanceToggleRequest,
    repo: SystemRepository = Depends(get_system_repository)
):
    await repo.set_maintenance_mode(payload.enabled, payload.message)
    return {"status": "updated", "is_maintenance": payload.enabled}