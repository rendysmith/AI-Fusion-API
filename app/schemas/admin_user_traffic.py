from datetime import datetime
from typing import Optional, List

from pydantic import BaseModel, ConfigDict


class UserTrafficSourceResponse(BaseModel):
    user_id: int
    email: Optional[str] = None
    username: Optional[str] = None
    created_at: datetime


    utm_source: Optional[str] = None
    utm_medium: Optional[str] = None
    utm_campaign: Optional[str] = None
    utm_term: Optional[str] = None
    referrer: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class UserTrafficListResponse(BaseModel):
    items: List[UserTrafficSourceResponse]
    total: int
    page: int
    limit: int