"""Billing service for text generation."""

import json
from fastapi import HTTPException, status
from app.database.repositories.ai_model_repository import AiModelRepository
from app.database.repositories.user_repository import UserRepository
from app.database.main_models import User
from app.schemas import ErrorDetailInsufficientCredits


class TextGenBillingService:
    """Service for processing payments for text generation."""

    def __init__(
        self,
        user_repo: UserRepository,
        ai_model_repo: AiModelRepository,
    ):
        self.user_repo = user_repo
        self.ai_model_repo = ai_model_repo

    async def process_payment(self, user: User, model_slug: str) -> float:
        """Check model cost, validate balance, and deduct funds.

        Returns the remaining balance after deduction.
        Raises HTTPException 402 if insufficient credits.
        """
        model_obj = await self.ai_model_repo.get_by_slug(model_slug)
        if not model_obj:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Model '{model_slug}' not found",
            )

        if not model_obj.is_available:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Model '{model_slug}' is currently unavailable",
            )

        settings_data = {}
        if isinstance(model_obj.settings, dict):
            settings_data = model_obj.settings
        elif isinstance(model_obj.settings, str):
            try:
                settings_data = json.loads(model_obj.settings)
            except Exception:
                settings_data = {}

        base_cost = float(settings_data.get("cost", 0.0))
        final_cost = round(base_cost * user.coefficient, 6)

        if final_cost <= 0:
            return 0.0

        if float(user.balance) < final_cost:
            error_detail = ErrorDetailInsufficientCredits(
                balance=float(user.balance),
                cost=final_cost,
                model=model_slug,
                plan=user.subscription.plan.slug if user.subscription else "none",
            )

            raise HTTPException(
                status_code=status.HTTP_402_PAYMENT_REQUIRED,
                detail=error_detail.model_dump(),
            )

        new_balance = await self.user_repo.deduct_balance(user.id, final_cost)

        if new_balance is None:
            raise HTTPException(
                status_code=status.HTTP_402_PAYMENT_REQUIRED,
                detail="Insufficient credits (concurrency check)",
            )

        return float(new_balance)
