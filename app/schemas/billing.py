from datetime import datetime
from pydantic import BaseModel, ConfigDict
from typing import Optional
from .subscription import SubscriptionDetailResponse

class CheckoutRequest(BaseModel):
    product_id: int

class CheckoutResponse(BaseModel):
    success: bool
    payment_link: str
    payment_id: str

class GetCourseWebhook(BaseModel):
    event_type: Optional[str] = None
    deal_id: Optional[str] = None
    deal_number: str
    deal_status: str
    class Config:
        extra = "ignore"

class PaymentStatusResponse(BaseModel):
    payment_id: str
    status: str
    provider: str
    subscription: Optional[SubscriptionDetailResponse] = None

class CanceledSubscriptionResponse(BaseModel):
    success: bool
    message: str
    subscription: SubscriptionDetailResponse

class InvoiceResponse(BaseModel):
    id: int
    subscription_id: Optional[str] = None
    amount: int
    status: str
    cloudpayments_transaction_id: Optional[str] = None
    failure_reason: Optional[str] = None
    paid_at: Optional[datetime] = None
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)