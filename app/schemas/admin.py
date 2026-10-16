"""Admin panel Pydantic schemas."""

from datetime import datetime, timedelta
from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional, Dict, Any
from .plan import AdminSubscriptionPlanResponse
from .subscription import SubscriptionDetailResponse


class AdminUserResponse(BaseModel):
    """Admin view of a user."""

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
    """Paginated admin user list."""

    users: List[AdminUserResponse]
    total: int
    page: int
    limit: int


class BlockUserRequest(BaseModel):
    """Request to block or unblock a user."""

    is_blocked: bool


class BlockUserResponse(BaseModel):
    """Response after blocking/unblocking a user."""

    uid: str
    username: Optional[str] = None
    email: Optional[str] = None
    is_blocked: bool
    is_admin: bool
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class UpdateSubscriptionRequest(BaseModel):
    """Request to update a user's subscription."""

    plan_id: int
    status: str = "active"
    period_start: Optional[datetime] = Field(default_factory=datetime.now)
    period_end: Optional[datetime] = Field(
        default_factory=lambda: datetime.now() + timedelta(days=30),
    )
    is_manual: bool = True


class UpdateSubscriptionResponse(BaseModel):
    """Response after updating a subscription."""

    subscription: SubscriptionDetailResponse
    success: bool = True


class AdminGenerationTaskUser(BaseModel):
    """Minimal user info for generation task admin view."""

    uid: str = Field(..., validation_alias="firebase_uid")
    email: Optional[str] = None
    username: Optional[str] = None

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class AdminGenerationTaskResponse(BaseModel):
    """Generation task as seen by admin."""

    id: str
    user: AdminGenerationTaskUser
    model_slug: str
    status: str
    error: Optional[str] = None
    cost: float
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AdminGenerationListResponse(BaseModel):
    """Paginated admin generation task list."""

    generations: List[AdminGenerationTaskResponse]
    total: int
    page: int
    limit: int


class RevenueMetrics(BaseModel):
    """Revenue metrics for admin dashboard."""

    total: float
    this_month: float
    last_month: float


class AdminMetricsResponse(BaseModel):
    """Admin dashboard metrics."""

    total_users: int
    active_subscriptions: int
    total_generations: int
    generations_today: int
    revenue: RevenueMetrics
    model_usage: Dict[str, int]
    plan_distribution: Dict[str, int]


class BulkCreditRequest(BaseModel):
    """Request to bulk-credit users."""

    identifiers: List[str]
    amount: int


class AdminTaskUserDetail(BaseModel):
    """Detailed user info for task admin view."""

    firebase_uid: str
    email: Optional[str] = None
    username: Optional[str] = None
    telegram_id: Optional[int] = None
    balance: float

    model_config = ConfigDict(from_attributes=True)


class AdminTaskDetailResponse(BaseModel):
    """Detailed admin view of a single task."""

    id: str
    status: str
    prompt: Optional[str] = None
    model_slug: str

    video_url: Optional[str] = None
    thumbnail_url: Optional[str] = None

    error: Optional[str] = None

    parameters: Dict[str, Any] = Field(default_factory=dict)

    cost: float
    credits_used: float

    user: Optional[AdminTaskUserDetail] = None

    created_at: datetime

    completed_at: Optional[datetime] = None
    started_at: Optional[datetime] = None

    external_task_id: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)
