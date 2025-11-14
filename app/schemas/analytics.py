from pydantic import BaseModel
from typing import List

class Balance(BaseModel):
    key_balance: float

class UserStatItem(BaseModel):
    model: str
    count: int

class DailyActivity(BaseModel):
    date: str
    count: int

class UserAnalyticsResponse(BaseModel):
    telegram_id: int
    total_spending: float
    total_tasks: int
    failed_tasks: int
    model_usage: List[UserStatItem]
    daily_activity: List[DailyActivity]