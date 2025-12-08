from datetime import datetime

from pydantic import BaseModel, ConfigDict
from uuid import UUID
from typing import Optional, List


class VisitorTrackRequest(BaseModel):
    visitor_id: UUID
    referrer: Optional[str] = None

    utm_source: Optional[str] = None
    utm_medium: Optional[str] = None
    utm_campaign: Optional[str] = None
    utm_content: Optional[str] = None
    utm_term: Optional[str] = None


class AnalyticsVisitors(BaseModel):
    total: int
    new: int
    repeat: int

class AnalyticsDailyResponse(BaseModel):
    visitors: AnalyticsVisitors
    telegram_signups: int
    purchases: int
    conversion_visitors_to_signups: float
    conversion_signups_to_purchases: float
    conversion_overall: float


class VisitorLogItem(BaseModel):
    visitor_id: UUID
    first_visit_at: datetime
    last_visit_at: datetime


    utm_source: Optional[str] = None
    utm_medium: Optional[str] = None
    utm_campaign: Optional[str] = None
    utm_term: Optional[str] = None
    utm_content: Optional[str] = None
    referrer: Optional[str] = None


    user_id: Optional[int] = None

    model_config = ConfigDict(from_attributes=True)


class VisitorLogResponse(BaseModel):
    items: List[VisitorLogItem]
    total: int
    page: int
    limit: int