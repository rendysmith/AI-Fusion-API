"""Referral system Pydantic schemas."""

from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from decimal import Decimal


class UserRegisterRequest(BaseModel):
    """Request to register a new user with optional referral code."""

    firebase_uid: str = Field(..., description="UID из Firebase")
    email: Optional[EmailStr] = None
    username: Optional[str] = None
    photo_url: Optional[str] = None
    referral_code: Optional[str] = None


class UserResponse(BaseModel):
    """User response with referral code."""

    id: int
    email: Optional[str]
    username: Optional[str]
    balance: Decimal
    referral_code: Optional[str]

    class Config:
        from_attributes = True
