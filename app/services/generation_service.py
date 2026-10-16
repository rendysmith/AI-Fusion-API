"""Generation service for preparing and dispatching generation tasks."""

import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import Tuple, Dict, Any, Optional

import aiobotocore
from fastapi import HTTPException
from starlette import status

from app import schemas
from app.database.ai import AiModel
from app.database.main_models import User
from app.database.repositories.ai_model_repository import AiModelRepository
from app.database.repositories.plan_access_repository import PlanAccessRepository
from app.database.repositories.task_repository import TaskRepository
from app.database.repositories.user_repository import UserRepository

from app.main_api_utils import get_final_cost

from app.schemas import AnyModelParams

from app.utils.image_processor import process_and_upload_images
from app.settings import settings


class GenerationService:
    """Service for preparing and validating generation tasks."""

    def __init__(
        self,
        user: User,
        ai_model_repo: AiModelRepository,
        user_repo: UserRepository,
        s3_client: aiobotocore.client.BaseClient,
        task_repo: TaskRepository,
        plan_access_repo: PlanAccessRepository,
    ):
        self.user = user
        self.ai_model_repo = ai_model_repo
        self.user_repo = user_repo
        self.s3_client = s3_client
        self.task_repo = task_repo
        self.plan_access_repo = plan_access_repo

    async def prepare_generation_task(
        self, model_params: AnyModelParams,
    ) -> Tuple[str, Dict[str, Any], Decimal]:
        """Validate, calculate cost, and prepare a generation task for queueing."""
        active_plan = await self.user_repo.get_user_active_plan(self.user.id)

        if not active_plan:
            raise HTTPException(
                status_code=status.HTTP_402_PAYMENT_REQUIRED,
                detail="No active subscription found. Please contact support.",
            )

        limit = active_plan.concurrent_generation_limit
        current_count = await self.task_repo.get_processing_task_count(self.user.id)

        if current_count >= limit:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Concurrent generation limit reached ({limit}). Please wait.",
            )

        model_name = model_params.model_name

        available_models = await self.plan_access_repo.get_models_for_plan(
            active_plan.id,
        )

        is_allowed = any(model.slug == model_name for model in available_models)

        if not is_allowed:
            raise HTTPException(
                status_code=status.HTTP_402_PAYMENT_REQUIRED,
                detail=(
                    f"Model '{model_name}' is not available for your "
                    f"current subscription plan ('{active_plan.slug}')."
                ),
            )

        processed_params = await process_and_upload_images(
            model_params=model_params,
            s3_client=self.s3_client,
            bucket_name=settings.YANDEX_BUCKET_NAME,
            endpoint_url=settings.YANDEX_STORAGE_ENDPOINT,
        )

        await self._validate_and_get_price(model_name)

        final_cost, prime_cost = await self._calculate_costs(processed_params)

        worker_should_delay = False

        if self.user.balance >= final_cost:
            worker_should_delay = False
        elif active_plan.has_unlimited and "sora" in model_name:
            final_cost = 0.0
            worker_should_delay = True
        else:
            error_payload = schemas.ErrorDetailInsufficientCredits(
                balance=float(self.user.balance),
                cost=final_cost,
                model=model_name,
                plan=active_plan.slug,
            )
            raise HTTPException(
                status_code=status.HTTP_402_PAYMENT_REQUIRED,
                detail=error_payload.model_dump(),
            )

        new_balance = await self._deduct_funds(final_cost)

        if new_balance is None:
            raise HTTPException(
                status_code=status.HTTP_402_PAYMENT_REQUIRED,
                detail="Insufficient credits",
            )

        task_id = str(uuid.uuid4())
        created_at = datetime.now(timezone.utc)

        task_message_body = self._prepare_task_message(
            task_id=task_id,
            model_params=processed_params,
            final_cost=final_cost,
            prime_cost=prime_cost,
            created_at=created_at,
            plan_is_unlimited=worker_should_delay,
            delay_factor=active_plan.unlimited_delay_factor,
        )

        await self.task_repo.create_pending_task(
            task_id=task_id,
            user_id=self.user.id,
            model_slug=processed_params.model_name,
            cost=final_cost,
            prime_cost=prime_cost,
            params=processed_params.model_dump(),
            created_at=created_at,
        )

        return task_id, task_message_body, new_balance

    def _prepare_task_message(
        self,
        task_id: str,
        model_params: schemas.AnyModelParams,
        final_cost: float,
        prime_cost: float,
        created_at: datetime,
        plan_is_unlimited: bool = False,
        delay_factor: float = 1.0,
    ) -> dict:
        """Prepare the message to be sent to the task queue."""
        return {
            "_id": task_id,
            "status": "pending",
            "user_id": self.user.id,
            "created_at": created_at.isoformat(),
            "model": model_params.model_name,
            "params": model_params.model_dump(),
            "cost": final_cost,
            "prime_cost": prime_cost,
            "plan_is_unlimited": plan_is_unlimited,
            "unlimited_delay_factor": delay_factor,
            "result": None,
            "error": None,
        }

    async def _validate_and_get_price(self, model_name: str) -> AiModel:
        """Validate that the model exists and is available."""
        price_obj = await self.ai_model_repo.get_by_slug(model_name)

        if not price_obj:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Price for model '{model_name}' is not set in the admin panel",
            )

        if not price_obj.is_available:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=(
                    f"Model '{model_name}' is temporarily disabled "
                    f"by the administrator"
                ),
            )

        return price_obj

    async def _calculate_costs(
        self, model_params: schemas.AnyModelParams,
    ) -> tuple[float, float]:
        """Calculate the final and prime cost for the generation."""
        model_name = model_params.model_name

        final_cost, prime_cost = await get_final_cost(
            user=self.user,
            model_name=model_name,
            model_params=model_params.model_dump(),
            ai_model_repo=self.ai_model_repo,
        )

        return final_cost, prime_cost

    async def _deduct_funds(self, amount: float) -> Optional[Decimal]:
        """Deduct funds from user balance."""
        new_balance = await self.user_repo.deduct_balance(
            user_id=self.user.id, amount=amount,
        )
        return new_balance
