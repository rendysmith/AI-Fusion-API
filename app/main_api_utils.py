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


    if not model_obj.settings or "cost" not in model_obj.settings:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Price for model '{model_name}' is not set in 'settings' JSON."
        )


    base_cost = float(model_obj.settings.get("cost", 0.0))
    base_prime_cost = float(model_obj.settings.get("prime_cost", 0.0))

    if model_name in settings.MODELS_WITH_DURATION_COST:
        multiplier = model_params.get('duration', 1) or 1
    else:
        multiplier = model_params.get('num_images', 1) or 1


    final_cost = round(base_cost * multiplier * user.coefficient, 6)
    prime_cost = round(base_prime_cost * multiplier, 6)

    return final_cost, prime_cost