from typing import List

from fastapi import APIRouter, HTTPException, status, Depends
from app import schemas
from app.database.main_models import User
from app.dependencies import get_llm_repository, get_image_repository
from app.main import AUTH_DEPENDENCY
from app.services.t2i_service import UniversalImageGenerator

router = APIRouter(prefix="/generation", tags=["AI Generation"])




@router.post(
    "/image_generation",
    response_model=List[schemas.GenerationResponse],
    summary="Запуск генерации изображения"
)
async def generate_image(
        payload: schemas.GenerateRequest,
        user: User = AUTH_DEPENDENCY,
        repo: UniversalImageGenerator = Depends(get_image_repository)
):

    result = await repo.get_response(
        user_id=user.id,
        model_slug=payload.model,
        prompt=payload.prompt)

    return {"result": result}

# @router.post(
#     "/result",
#     response_model=schemas.PollingResponseWrapper,
#     summary="Получение результата генерации (Polling)"
# )
# async def get_generation_result(
#         payload: schemas.GetResultRequest,
#         client: httpx.AsyncClient = Depends(get_http_client)
# ):
#     """
#     Проверяет статус задачи по ID.
#     Используется, если генерация не стриминговая и не через вебхук.
#     """
#     try:
#         response = await client.post("/v1/draw/result", json={"id": payload.id})
#
#         if response.status_code != 200:
#             raise HTTPException(
#                 status_code=response.status_code,
#                 detail=f"External API error: {response.text}"
#             )
#
#         result = response.json()
#
#         # Проверка логического кода ошибки от Nano Banana
#         if result.get("code") != 0:
#             raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=result.get("msg", "Unknown error"))
#
#         return result
#
#     except httpx.RequestError as exc:
#         raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, detail=f"Connection error: {exc}")