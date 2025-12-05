import json

from fastapi import HTTPException
from starlette import status


from app.database.main_models import User
from app.database.repositories.ai_model_repository import AiModelRepository
from app.settings import settings


async def get_final_cost(
        user: User,
        model_name: str,
        model_params: dict,
        ai_model_repo: AiModelRepository,
) -> tuple[float, float]:
    model_obj = await ai_model_repo.get_by_slug(model_name)
    if not model_obj:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Model '{model_name}' not found in ai_models table."
        )

    settings_data = {}
    if isinstance(model_obj.settings, str):
        try:
            settings_data = json.loads(model_obj.settings)
        except:
            pass
    elif isinstance(model_obj.settings, dict):
        settings_data = model_obj.settings

    base_cost = float(settings_data.get("cost", 0.0))
    base_prime_cost = float(settings_data.get("prime_cost", 0.0))

    unit_type = settings_data.get("unit")

    multiplier = 1.0

    if unit_type == "video":
        multiplier = 1.0


    elif unit_type == "second" or model_name in settings.MODELS_WITH_DURATION_COST:
        multiplier = float(model_params.get('duration', 1) or 1)

    else:
        multiplier = float(model_params.get('num_images', 1) or 1)

    final_cost = round(base_cost * multiplier * user.coefficient, 6)
    prime_cost = round(base_prime_cost * multiplier, 6)

    return final_cost, prime_cost