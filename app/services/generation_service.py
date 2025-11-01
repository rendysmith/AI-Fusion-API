import uuid
from datetime import datetime, timezone
from typing import Tuple, Dict, Any

from fastapi import HTTPException
from starlette import status

from app import schemas
from app.database.main_models import User, Price
from app.database.repositories.price_repository import PriceRepository
from app.database.repositories.user_repository import UserRepository

from app.main_api_utils import get_final_cost

from app.schemas import AnyModelParams


class GenerationService:

    def __init__(
            self,
            user: User,
            price_repo: PriceRepository,
            user_repo: UserRepository,
    ):
        self.user = user
        self.price_repo = price_repo
        self.user_repo = user_repo

    async def prepare_generation_task(
            self, model_params: AnyModelParams
    ) -> Tuple[str, Dict[str, Any]]:

        model_name = model_params.model_name

        await self._validate_and_get_price(model_name)
        final_cost, prime_cost = await self._calculate_costs(model_params)

        # logger.info(f"Task Cost: {final_cost}. User {self.user.id} Balance: {self.user.balance}")
        # await self._deduct_funds(final_cost)

        task_id = str(uuid.uuid4())

        task_message_body = self._prepare_task_message(
            task_id, model_params, final_cost, prime_cost
        )

        return task_id, task_message_body

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

    async def _validate_and_get_price(self, model_name: str) -> Price:

        price_obj = await self.price_repo.get_by_model_name(model_name)

        if not price_obj:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Price for model '{model_name}' is not set in the admin panel",
            )

        if not price_obj.is_active:
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
            model_params=model_params.dict(),
            price_repo=self.price_repo,
        )

        return final_cost, prime_cost

    async def _deduct_funds(self, amount: float):

        was_deducted = await self.user_repo.deduct_balance(
            user_id=self.user.id, amount=amount
        )

        if not was_deducted:
            raise HTTPException(
                status_code=status.HTTP_402_PAYMENT_REQUIRED,
                detail=f"Insufficient funds. Required: {amount}. Please top up your balance.",
            )