"""User profile and balance Pydantic schemas."""

import re
from pydantic import BaseModel, Field, field_validator, ConfigDict
from typing import Optional
from uuid import UUID

from .subscription import SubscriptionDetailResponse
from .plan import SubscriptionPlanResponse


class UserBalanceResponse(BaseModel):
    """User balance with current plan info."""

    balance: float
    plan: Optional[str] = None
    generations_left: Optional[int] = None


class UserProfileResponse(BaseModel):
    """Full user profile returned to the client."""

    uid: str = Field(validation_alias="firebase_uid")

    email: Optional[str] = None
    username: Optional[str] = None

    display_name: Optional[str] = None
    photo_url: Optional[str] = None
    balance: float
    currency: str = "RUB"
    is_admin: bool = False

    current_plan: Optional[SubscriptionPlanResponse] = None
    subscription: Optional[SubscriptionDetailResponse] = None

    telegram_id: Optional[int] = None
    telegram_username: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class UserProfileUpdateRequest(BaseModel):
    """Request to update user profile fields."""

    username: Optional[str] = Field(None, min_length=3, max_length=30)
    visitor_id: Optional[UUID] = None
    display_name: Optional[str] = Field(None, max_length=100)
    photo_url: Optional[str] = Field(None, max_length=255)

    @classmethod
    @field_validator("username")
    def validate_username(cls, v: Optional[str]) -> Optional[str]:
        """Validate that username contains only safe characters."""
        if v is None:
            return v
        if not re.match(r"^[a-zA-Z0-9_]+$", v):
            raise ValueError("Username must contain only letters, numbers, and underscores")
        return v
