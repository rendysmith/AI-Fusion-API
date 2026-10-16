"""Subscription and plan Pydantic schemas."""

from datetime import datetime
from pydantic import BaseModel, ConfigDict
from typing import Optional, List
from .plan import AdminSubscriptionPlanResponse, SubscriptionPlanResponse


class AvailableModel(BaseModel):
    """AI model available to a subscription plan."""

    id: int
    name: str
    slug: str
    category: str
    model_config = ConfigDict(from_attributes=True)


class SubscriptionUsage(BaseModel):
    """Usage statistics for a subscription."""

    today: int
    concurrent: int
    is_unlimited: bool = False


class SubscriptionDetailResponse(BaseModel):
    """Detailed subscription information."""

    id: str
    user_id: int
    plan_id: int
    status: str
    is_manual: bool
    current_period_start: Optional[datetime] = None
    current_period_end: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    plan: AdminSubscriptionPlanResponse
    model_config = ConfigDict(from_attributes=True)


class UserSubscriptionDetailResponse(BaseModel):
    """User's subscription with available models and usage."""

    plan: Optional[SubscriptionPlanResponse] = None
    available_models: List[AvailableModel]
    usage: SubscriptionUsage
