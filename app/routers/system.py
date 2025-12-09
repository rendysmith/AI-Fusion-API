from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.database.repositories.ai_model_repository import AiModelRepository
from app.database.repositories.circuit_breaker_repository import CircuitBreakerRepository
from app.dependencies import get_system_repository, get_current_admin_user, get_circuit_breaker_repository, \
    get_ai_model_repository
from app.database.repositories.system_repository import SystemRepository
from app.schemas import SystemHealthResponse, ServiceStatusItem

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


@router.get(
    "/services/health",
    response_model=SystemHealthResponse,
    dependencies=[Depends(get_current_admin_user)],
    summary="[Admin] Get status of AI providers (Circuit Breakers)"
)
async def get_services_health(
        cb_repo: CircuitBreakerRepository = Depends(get_circuit_breaker_repository),
        model_repo: AiModelRepository = Depends(get_ai_model_repository)
):

    all_models = await model_repo.get_all_by_category(category=None)

    health_status = []

    for model in all_models:

        is_open = await cb_repo.is_open(model.slug)
        last_error = None

        if is_open:
            last_error = await cb_repo.get_last_error(model.slug)

        health_status.append(
            ServiceStatusItem(
                model_slug=model.slug,
                model_name=model.name,
                provider=model.provider,
                is_circuit_open=is_open,
                last_error=last_error
            )
        )

    return SystemHealthResponse(services=health_status)



@router.post(
    "/services/{model_slug}/reset",
    dependencies=[Depends(get_current_admin_user)],
    summary="[Admin] Manually close the circuit (reset error)"
)
async def reset_service_circuit(
        model_slug: str,
        cb_repo: CircuitBreakerRepository = Depends(get_circuit_breaker_repository)
):
    await cb_repo.reset(model_slug)
    return {"status": "success", "message": f"Circuit for {model_slug} has been reset."}