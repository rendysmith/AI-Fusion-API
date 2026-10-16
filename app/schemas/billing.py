"""Billing and payment Pydantic schemas."""

from datetime import datetime
from pydantic import BaseModel, ConfigDict
from typing import Optional, List
from .subscription import SubscriptionDetailResponse


class CheckoutRequest(BaseModel):
    """Request to create a checkout for a product."""

    product_id: int


class CheckoutResponse(BaseModel):
    """Response with payment link after checkout creation."""

    success: bool
    payment_link: str
    payment_id: str


class GetCourseWebhook(BaseModel):
    """Webhook payload from GetCourse."""

    event_type: Optional[str] = None
    deal_id: Optional[str] = None
    deal_number: str
    deal_status: str

    class Config:
        extra = "ignore"


class PaymentStatusResponse(BaseModel):
    """Status of a payment."""

    payment_id: str
    status: str
    provider: str
    subscription: Optional[SubscriptionDetailResponse] = None


class CanceledSubscriptionResponse(BaseModel):
    """Response after canceling a subscription."""

    success: bool
    message: str
    subscription: SubscriptionDetailResponse


class InvoiceResponse(BaseModel):
    """Invoice record for a completed payment."""

    id: int
    subscription_id: Optional[str] = None
    amount: int
    status: str
    cloudpayments_transaction_id: Optional[str] = None
    failure_reason: Optional[str] = None
    paid_at: Optional[datetime] = None
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class BillingSubscriptionDetailResponse(BaseModel):
    """Billing details with subscription and invoices."""

    subscription: Optional[SubscriptionDetailResponse] = None
    invoices: List[InvoiceResponse]


class ErrorDetailInsufficientCredits(BaseModel):
    """Error details when user has insufficient credits."""

    status: int = 402
    message: str = "Insufficient credits"
    detail: str = "User balance is insufficient for this generation"
    balance: float
    cost: float
    model: Optional[str] = None
    plan: Optional[str] = None
