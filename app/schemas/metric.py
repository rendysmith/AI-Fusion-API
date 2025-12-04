from pydantic import BaseModel
from uuid import UUID
from typing import Optional

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