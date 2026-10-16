"""Admin user detail Pydantic schemas."""

from datetime import datetime
from pydantic import BaseModel, ConfigDict
from typing import Optional, List
from .subscription import SubscriptionDetailResponse


class UserUsageStats(BaseModel):
    """User generation and spending statistics."""

    total_generations: int
    successful_generations: int
    total_credits_spent: float
    total_money_paid: float


class UserTrafficInfo(BaseModel):
    """User traffic source information."""

    first_visit_at: Optional[datetime] = None
    utm_source: Optional[str] = None
    utm_medium: Optional[str] = None
    utm_campaign: Optional[str] = None
    utm_term: Optional[str] = None
    referrer: Optional[str] = None


class AdminUserFullDetailResponse(BaseModel):
    """Full user detail for admin panel."""

    id: int
    firebase_uid: str
    email: Optional[str] = None
    username: Optional[str] = None
    telegram_id: Optional[int] = None
    balance: float
    is_admin: bool
    is_blocked: bool
    created_at: datetime

    subscription: Optional[SubscriptionDetailResponse] = None

    stats: UserUsageStats
    traffic: UserTrafficInfo

    model_config = ConfigDict(from_attributes=True)
