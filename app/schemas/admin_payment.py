from datetime import datetime
from pydantic import BaseModel, ConfigDict
from typing import Optional, List


class AdminPaymentItem(BaseModel):
    internal_id: str
    amount: float
    currency: str
    status: str
    provider: str
    created_at: datetime

    user_email: Optional[str] = None
    user_id: int
    product_name: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class AdminPaymentListResponse(BaseModel):
    items: List[AdminPaymentItem]
    total: int
    page: int
    limit: int