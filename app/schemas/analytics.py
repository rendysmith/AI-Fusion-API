"""Analytics Pydantic schemas."""

from pydantic import BaseModel
from typing import List


class Balance(BaseModel):
    """User balance key-value pair."""

    key_balance: float


class UserStatItem(BaseModel):
    """Per-model usage statistic."""

    model: str
    count: int


class DailyActivity(BaseModel):
    """Daily activity count."""

    date: str
    count: int


class UserAnalyticsResponse(BaseModel):
    """User analytics with spending, tasks and model usage."""

    telegram_id: int
    total_spending: float
    total_tasks: int
    failed_tasks: int
    model_usage: List[UserStatItem]
    daily_activity: List[DailyActivity]
