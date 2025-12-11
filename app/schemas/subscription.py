from datetime import datetime
from pydantic import BaseModel, ConfigDict
from typing import Optional, List
from .plan import AdminSubscriptionPlanResponse, SubscriptionPlanResponse


class AvailableModel(BaseModel):
    id: int
    name: str
    slug: str
    category: str
    model_config = ConfigDict(from_attributes=True)

class SubscriptionUsage(BaseModel):
    today: int
    concurrent: int
    is_unlimited: bool = False

class SubscriptionDetailResponse(BaseModel):
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
    plan: Optional[SubscriptionPlanResponse] = None
    available_models: List[AvailableModel]
    usage: SubscriptionUsage