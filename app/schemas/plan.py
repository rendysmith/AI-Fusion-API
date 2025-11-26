from datetime import datetime
from pydantic import BaseModel, Field, field_validator, ConfigDict, field_serializer
from typing import Optional



class PlanSchema(BaseModel):
    id: int
    name: str
    slug: str
    generations_per_month: int = Field(alias="generationsPerMonth")


class SubscriptionSchema(BaseModel):
    status: str
    current_period_end: datetime = Field(alias="currentPeriodEnd")



class SubscriptionPlanBase(BaseModel):
    name: str = Field(..., min_length=1)
    slug: str = Field(..., min_length=1, pattern=r'^[a-z0-9-]+$')
    description: str
    price: int = Field(..., ge=0)
    credits_granted: int = Field(..., ge=0)
    concurrent_generation_limit: int = Field(..., ge=1)
    sort_order: int = 0
    is_active: bool
    has_unlimited: bool = False


class SubscriptionPlanCreate(SubscriptionPlanBase):
    is_active: bool | int
    has_unlimited: bool | int

    @classmethod
    @field_validator('is_active','has_unlimited', mode='before')
    def convert_int_to_bool(cls, v):
        return bool(v)


class SubscriptionPlanUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1)
    slug: Optional[str] = Field(None, min_length=1, pattern=r'^[a-z0-9-]+$')
    description: Optional[str] = None
    price: Optional[int] = Field(None, ge=0)
    credits_granted: Optional[int] = Field(None, ge=0)
    concurrent_generation_limit: Optional[int] = Field(None, ge=1)
    sort_order: Optional[int] = None
    is_active: Optional[bool | int] = None
    has_unlimited: Optional[bool | int] = None

    @classmethod
    @field_validator('is_active', 'has_unlimited', mode='before')
    def convert_int_to_bool_opt(cls, v):
        if v is not None:
            return bool(v)
        return v


class SubscriptionPlanResponse(SubscriptionPlanBase):
    id: int
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)


class AdminSubscriptionPlanResponse(SubscriptionPlanResponse):
    @field_serializer('is_active')
    def serialize_is_active(self, value: bool) -> bool:
        return value