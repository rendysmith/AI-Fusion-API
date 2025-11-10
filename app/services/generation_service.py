import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import Tuple, Dict, Any

import aiobotocore
from fastapi import HTTPException
from starlette import status

from app import schemas
from app.database.billing_models import AiModel
from app.database.main_models import User, Price
from app.database.repositories.ai_model_repository import AiModelRepository
from app.database.repositories.user_repository import UserRepository

from app.main_api_utils import get_final_cost

from app.schemas import AnyModelParams

from app.utils.image_processor import process_and_upload_images
from app.settings import settings


class GenerationService:

    def __init__(
            self,
            user: User,
            ai_model_repo: AiModelRepository,
            user_repo: UserRepository,
            s3_client: aiobotocore.client.BaseClient
    ):
        self.user = user
        self.ai_model_repo = ai_model_repo
        self.user_repo = user_repo
        self.s3_client = s3_client

    async def prepare_generation_task(
            self, model_params: AnyModelParams
    ) -> Tuple[str, Dict[str, Any], Decimal]:

        model_name = model_params.model_name

        processed_params = await process_and_upload_images(
            model_params=model_params,
            s3_client=self.s3_client,
            bucket_name=settings.YANDEX_BUCKET_NAME,
            endpoint_url=settings.YANDEX_STORAGE_ENDPOINT
        )


        await self._validate_and_get_price(model_name)
        final_cost, prime_cost = await self._calculate_costs(processed_params)


        new_balance = await self._deduct_funds(final_cost)

        task_id = str(uuid.uuid4())

        task_message_body = self._prepare_task_message(
            task_id, processed_params, final_cost, prime_cost
        )

        return task_id, task_message_body, new_balance

    def _prepare_task_message(
            self,
            task_id: str,
            model_params: schemas.AnyModelParams,
            final_cost: float,
            prime_cost: float,
    ) -> dict:

        return {
            "_id": task_id,
            "status": "pending",
            "user_id": self.user.id,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "model": model_params.model_name,
            "params": model_params.dict(),
            "cost": final_cost,
            "prime_cost": prime_cost,
            "result": None,
            "error": None,
        }

    async def _validate_and_get_price(self, model_name: str) -> AiModel:

        price_obj = await self.ai_model_repo.get_by_slug(model_name)

        if not price_obj:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Price for model '{model_name}' is not set in the admin panel",
            )

        if not price_obj.is_available:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Model '{model_name}' is temporarily disabled by the administrator",
            )

        return price_obj

    async def _calculate_costs(self, model_params: schemas.AnyModelParams) -> tuple[float, float]:

        model_name = model_params.model_name

        final_cost, prime_cost = await get_final_cost(
            user=self.user,
            model_name=model_name,
            model_params=model_params.model_dump(),
            ai_model_repo=self.ai_model_repo,
        )

        return final_cost, prime_cost

    async def _deduct_funds(self, amount: float) -> Decimal:

        new_balance = await self.user_repo.deduct_balance(
            user_id=self.user.id, amount=amount
        )

        if new_balance is None:
            raise HTTPException(
                status_code=status.HTTP_402_PAYMENT_REQUIRED,
                detail=f"Insufficient funds. Required: {amount}. Please top up your balance.",
            )

        return new_balance