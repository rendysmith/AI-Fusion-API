from datetime import datetime, timedelta
from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional, Dict
from .plan import AdminSubscriptionPlanResponse
from .subscription import SubscriptionDetailResponse

class AdminUserResponse(BaseModel):
    uid: str = Field(..., alias="id", validation_alias="firebase_uid")
    username: Optional[str] = None
    email: Optional[str] = None
    telegram_id: Optional[int] = None
    telegram_username: Optional[str] = None
    is_admin: bool
    is_blocked: bool
    created_at: datetime
    current_plan: Optional[AdminSubscriptionPlanResponse] = None
    subscription: Optional[SubscriptionDetailResponse] = None
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

class AdminUserListResponse(BaseModel):
    users: List[AdminUserResponse]
    total: int
    page: int
    limit: int

class BlockUserRequest(BaseModel):
    is_blocked: bool

class BlockUserResponse(BaseModel):
    uid: str
    username: Optional[str] = None
    email: Optional[str] = None
    is_blocked: bool
    is_admin: bool
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

class UpdateSubscriptionRequest(BaseModel):
    plan_id: int
    status: str = "active"
    period_start: Optional[datetime] = Field(default_factory=datetime.now)
    period_end: Optional[datetime] = Field(default_factory=lambda: datetime.now() + timedelta(days=30))
    is_manual: bool = True

class UpdateSubscriptionResponse(BaseModel):
    subscription: SubscriptionDetailResponse
    success: bool = True


class AdminGenerationTaskUser(BaseModel):

    uid: str = Field(..., validation_alias="firebase_uid")
    email: Optional[str] = None
    username: Optional[str] = None

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class AdminGenerationTaskResponse(BaseModel):
    id: str
    user: AdminGenerationTaskUser
    model_slug: str
    status: str
    error: Optional[str] = None
    cost: float
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AdminGenerationListResponse(BaseModel):
    generations: List[AdminGenerationTaskResponse]
    total: int
    page: int
    limit: int


class RevenueMetrics(BaseModel):
    total: float
    this_month: float
    last_month: float


class AdminMetricsResponse(BaseModel):
    total_users: int
    active_subscriptions: int
    total_generations: int
    generations_today: int
    revenue: RevenueMetrics
    model_usage: Dict[str, int]
    plan_distribution: Dict[str, int]